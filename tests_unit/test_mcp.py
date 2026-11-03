"""Fast adapter tests without a Frappe site; service integration lives in app tests."""

import base64
import importlib
import sys
import types
from pathlib import Path
from unittest.mock import MagicMock, patch

import fitz
import pytest
from jsonschema import Draft7Validator

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


class ValidationError(Exception):
	pass


class PermissionError(Exception):
	pass


def fail(message, exc=ValidationError):
	raise exc(message)


frappe = types.ModuleType("frappe")
frappe.throw = fail
frappe.ValidationError = ValidationError
frappe.PermissionError = PermissionError
frappe.session = types.SimpleNamespace(user="test@example.test")
frappe.has_permission = MagicMock(return_value=True)
frappe.get_doc = MagicMock()
frappe.db = MagicMock()
frappe.utils = types.SimpleNamespace(get_url=lambda path: "https://erp.example.test" + path)
frappe.whitelist = lambda *args, **kwargs: lambda fn: fn
sys.modules["frappe"] = frappe
for name in ("builder", "envelope", "template"):
	sys.modules["nesscale_sign.api." + name] = MagicMock()
from nesscale_sign.mcp import actions, files, tools
from nesscale_sign.mcp.catalog import EXTENSIONS


@pytest.fixture(autouse=True)
def reset():
	frappe.session.user = "test@example.test"
	frappe.has_permission.reset_mock(side_effect=True)
	frappe.get_doc.reset_mock(side_effect=True)
	frappe.db.reset_mock(side_effect=True)


def pdf_bytes():
	with fitz.open() as pdf:
		pdf.new_page(width=595, height=842)
		return pdf.tobytes()


def test_schemas_hooks_and_example():
	from nesscale_sign import hooks

	registered = {p.split(".")[-2] for p in hooks.assistant_tools}
	assert registered == set(tools.TOOLS)
	for spec in tools.definitions():
		Draft7Validator.check_schema(spec["inputSchema"])
	Draft7Validator(tools.TOOLS["esign_create_draft"][1]).validate(tools.guide()["example"])


def test_primary_mcp_actions_discover_workflow_guide():
	for name in (
		"esign_builder_guide",
		"esign_upload_pdf",
		"esign_create_draft",
		"esign_send_document",
	):
		assert "esign_workflow_guide" in tools.TOOLS[name][0]


@pytest.mark.parametrize("name", list(tools.TOOLS))
def test_all_tools_reject_guest(name):
	frappe.session.user = "Guest"
	with pytest.raises(PermissionError):
		tools.execute(name, {})


@pytest.mark.parametrize("name", list(tools.TOOLS))
def test_all_tools_reject_unknown_argument(name):
	with pytest.raises(ValidationError):
		tools.execute(name, {"arbitrary_python_method": "frappe.db.sql"})


@pytest.mark.parametrize(
	"data",
	[
		{"status": "Completed"},
		{"signers": [{"signer_name": "A", "signer_email": "a@example.test", "token": "secret"}]},
		{"signers": [{"signer_name": "A", "signer_email": "a@example.test", "status": "Signed"}]},
	],
)
def test_lifecycle_injection_rejected(data):
	with pytest.raises(ValidationError):
		tools.execute("esign_create_draft", {"data": data, "pdf_file": "/private/files/a.pdf"})


@pytest.mark.parametrize(
	"filename,payload",
	[
		("../escape.pdf", "YQ=="),
		("https://example.test/a.pdf", "YQ=="),
		("bad.pdf", "%%%"),
		("text.pdf", "YQ=="),
		("empty.pdf", ""),
	],
)
def test_upload_invalid(filename, payload):
	with pytest.raises(ValidationError), patch.object(files, "save_private_file") as save:
		tools.execute("esign_upload_pdf", {"file_name": filename, "content_base64": payload})
		save.assert_not_called()


def test_pdf_upload_round_trip():
	content = pdf_bytes()
	file = types.SimpleNamespace(file_name="test.pdf", file_url="/private/files/test.pdf", name="FILE-1")
	with patch.object(files, "save_private_file", return_value=file) as save:
		result = tools.execute(
			"esign_upload_pdf",
			{"file_name": "test.pdf", "content_base64": base64.b64encode(content).decode()},
		)
		save.assert_called_once_with("test.pdf", content)
	assert result["page_count"] == 1
	assert result["pages"][0]["height"] == 842
	chunks = [
		files._chunk(file.file_url, content, offset=i, length=97, include_content=True)
		for i in range(0, len(content), 97)
	]
	assert b"".join(base64.b64decode(c["content_base64"]) for c in chunks) == content
	assert chunks[-1]["eof"]
	assert "content_base64" not in files._chunk(file.file_url, content)


def test_upload_permission_checked_before_save():
	frappe.has_permission.side_effect = PermissionError
	with pytest.raises(PermissionError), patch.object(files, "save_private_file") as save:
		tools.execute(
			"esign_upload_pdf",
			{"file_name": "test.pdf", "content_base64": base64.b64encode(pdf_bytes()).decode()},
		)
		save.assert_not_called()


def test_download_checks_permission_before_bytes():
	frappe.get_doc.return_value.check_permission.side_effect = PermissionError
	with pytest.raises(PermissionError), patch.object(files, "read_file_content") as read:
		tools.execute("esign_download_file", {"file_url": "/private/files/private.pdf"})
		read.assert_not_called()
	frappe.get_doc.return_value.check_permission.side_effect = None


def test_encrypted_pdf_rejected():
	with fitz.open() as pdf:
		pdf.new_page()
		content = pdf.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="password")
	with pytest.raises(ValidationError):
		tools.execute(
			"esign_upload_pdf",
			{"file_name": "test.pdf", "content_base64": base64.b64encode(content).decode()},
		)


def test_inbox_removes_tokens():
	with patch.object(
		actions.envelope, "my_pending_signatures", return_value=[{"name": "ENV-1", "token": "bearer"}]
	):
		assert actions.my_pending_signatures()["documents"] == [{"name": "ENV-1"}]


def test_send_retry_skips_invitation():
	doc = MagicMock(name="ENV-1")
	doc.status = "Sent"
	frappe.get_doc.return_value = doc
	with patch.object(tools.envelope, "send_envelope") as send:
		assert tools.execute("esign_send_document", {"name": "ENV-1"})["already_sent"]
		send.assert_not_called()


def test_update_sent_rejected():
	doc = MagicMock()
	doc.status = "Sent"
	frappe.get_doc.return_value = doc
	with pytest.raises(ValidationError), patch.object(tools.envelope, "update_envelope") as update:
		tools.execute("esign_update_draft", {"name": "ENV-1", "data": {"title": "Changed"}})
		update.assert_not_called()


def test_finalization_requires_all_signatures():
	doc = MagicMock()
	doc.status = "In Progress"
	doc.signers = [types.SimpleNamespace(status="Sent")]
	frappe.get_doc.return_value = doc
	with pytest.raises(ValidationError), patch.object(actions.envelope, "retry_completion") as retry:
		actions.retry_completion("ENV-1")
		retry.assert_not_called()


def test_annotations_mark_external_and_destructive_operations():
	specs = {s["name"]: s for s in tools.definitions()}
	assert specs["esign_remind_document"]["annotations"]["openWorldHint"]
	assert not specs["esign_resend_invitation"]["annotations"]["idempotentHint"]
	assert specs["esign_delete_draft"]["annotations"]["destructiveHint"]


def test_fac_adapter_discovery_rollback_and_log_redaction():
	class BaseTool:
		def to_mcp_format(self):
			return {"name": self.name}

	module = types.ModuleType("frappe_assistant_core.core.base_tool")
	module.BaseTool = BaseTool
	with patch.dict(sys.modules, {"frappe_assistant_core.core.base_tool": module}):
		from nesscale_sign.mcp import fac

		for name in tools.TOOLS:
			adapter = importlib.import_module("nesscale_sign.mcp.fac_plugin.tools." + name).Tool()
			assert adapter.name == name
			assert "annotations" in adapter.to_mcp_format()
			assert "password" not in str(adapter._sanitize_arguments({"data": {"password": "sensitive"}}))
		adapter = fac.make_tool("esign_upload_pdf")()
		with (
			patch.object(fac, "execute", side_effect=RuntimeError("confidential")),
			pytest.raises(ValidationError) as error,
		):
			adapter.execute({"content_base64": "confidential"})
		assert "confidential" not in str(error.value)
		frappe.db.rollback.assert_called_with(save_point="esign_tool")


def test_metadata_sync_preserves_admin_access_and_category_override():
	from nesscale_sign.mcp.install import sync_tool_metadata

	frappe.get_installed_apps = lambda: ["frappe", "nesscale_sign", "frappe_assistant_core"]
	frappe.db.table_exists.return_value = True
	frappe.db.exists.return_value = True
	doc = types.SimpleNamespace(source_app="nesscale_sign", category_override=True)
	frappe.get_doc.return_value = doc
	sync_tool_metadata()
	for call in frappe.db.set_value.call_args_list:
		assert set(call.args[2]) == {"description", "auto_detected_category"}
	frappe.db.set_value.reset_mock()
	doc.category_override = False
	sync_tool_metadata()
	categories = {call.args[1]: call.args[2]["tool_category"] for call in frappe.db.set_value.call_args_list}
	assert categories["esign_workflow_guide"] == "read_only"
	assert categories["esign_send_document"] == "read_write"


def test_every_forwarded_target_accepts_its_schema_arguments():
	import ast

	for target, _, schema, _ in EXTENSIONS.values():
		module, method = target.rsplit(".", 1)
		tree = ast.parse((ROOT / "nesscale_sign" / (module.replace(".", "/") + ".py")).read_text())
		function = next(
			node for node in tree.body if isinstance(node, ast.FunctionDef) and node.name == method
		)
		if not function.args.kwarg:
			assert set(schema["properties"]) <= {arg.arg for arg in function.args.args}, target
