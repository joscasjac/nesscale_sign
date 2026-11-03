"""Assistant actions preserve permissions and signing lifecycle."""

import json
from unittest.mock import patch

import fitz
import frappe
from frappe.tests.utils import FrappeTestCase

from nesscale_sign.mcp.tools import definitions, execute, guide
from nesscale_sign.tests.utils import make_template
from nesscale_sign.utils.files import read_file_content


class TestMCPTools(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_build_draft_and_update_title_without_email(self):
		args = guide()["example"]
		block = args["content"]["pages"][0]["blocks"][0]
		block.pop("html")
		block["text"] = "{{document.title}}"
		with patch("frappe.sendmail") as send:
			result = execute("esign_create_draft", args)
			updated = execute(
				"esign_update_draft", {"name": result["name"], "data": {"title": "Updated agreement"}}
			)
			send.assert_not_called()
		self.assertEqual(result["status"], "Draft")
		self.assertIn(result["name"], result["editor_url"])
		self.assertTrue(json.loads(result["builder_json"])["pages"])
		fetched = execute("esign_get_document", {"name": result["name"]})
		self.assertEqual(len(fetched["fields"]), 1)
		self.assertNotIn("token", fetched["envelope"]["signers"][0])
		with fitz.open(stream=read_file_content(updated["source_pdf"]), filetype="pdf") as pdf:
			self.assertIn("Updated agreement", pdf[0].get_text())

	def test_template_and_send_retry_does_not_send_twice(self):
		tmpl = make_template()
		result = execute(
			"esign_create_draft",
			{
				"template_name": tmpl.name,
				"data": {
					"title": "Template draft",
					"signers": [
						{"role_key": "signer", "signer_name": "Test", "signer_email": "test@example.test"}
					],
				},
			},
		)
		with patch("frappe.sendmail") as send:
			execute("esign_send_document", {"name": result["name"]})
			count = send.call_count
			self.assertGreater(count, 0)
			retry = execute("esign_send_document", {"name": result["name"]})
			self.assertTrue(retry["already_sent"])
			self.assertEqual(send.call_count, count)
		with self.assertRaises(frappe.ValidationError):
			execute("esign_update_draft", {"name": result["name"], "data": {"title": "Forbidden edit"}})

	def test_permissions_and_invalid_inputs(self):
		with patch("frappe.has_permission", side_effect=frappe.PermissionError):
			with self.assertRaises(frappe.PermissionError):
				execute("esign_create_draft", guide()["example"])
		with self.assertRaises(frappe.ValidationError):
			execute("esign_send_document", {"name": "x", "force": True})
		with self.assertRaises(frappe.ValidationError):
			execute("esign_create_draft", {**guide()["example"], "pdf_file": "/private/files/x.pdf"})

	def test_guest_cannot_use_any_action(self):
		frappe.set_user("Guest")
		for spec in definitions():
			with self.assertRaises(frappe.PermissionError):
				execute(spec["name"], {})

	def test_read_tools_are_labeled(self):
		tools = {s["name"]: s for s in definitions()}
		self.assertTrue(tools["esign_get_document"]["annotations"]["readOnlyHint"])
		self.assertFalse(tools["esign_send_document"]["annotations"]["readOnlyHint"])

	def test_upload_inspect_and_download_pdf_chunks(self):
		import base64
		import hashlib

		with fitz.open() as pdf:
			pdf.new_page(width=595, height=842)
			content = pdf.tobytes()
		result = execute(
			"esign_upload_pdf",
			{"file_name": "mcp-test.pdf", "content_base64": base64.b64encode(content).decode()},
		)
		self.assertTrue(result["file_url"].startswith("/private/files/"))
		self.assertEqual(result["sha256"], hashlib.sha256(content).hexdigest())
		self.assertEqual(execute("esign_inspect_pdf", {"file_url": result["file_url"]})["page_count"], 1)
		chunks = []
		offset = 0
		while True:
			chunk = execute(
				"esign_download_file",
				{"file_url": result["file_url"], "offset": offset, "length": 97, "include_content": True},
			)
			chunks.append(base64.b64decode(chunk["content_base64"]))
			if chunk["eof"]:
				break
			offset = chunk["next_offset"]
		self.assertEqual(b"".join(chunks), content)

	def test_pdf_upload_rejects_paths_invalid_bytes_and_encrypted_pdf(self):
		import base64

		for file_name, payload in [("../escape.pdf", "YQ=="), ("invalid.pdf", "!"), ("text.pdf", "YQ==")]:
			with self.assertRaises(frappe.ValidationError):
				execute("esign_upload_pdf", {"file_name": file_name, "content_base64": payload})
		with fitz.open() as pdf:
			pdf.new_page()
			content = pdf.tobytes(encryption=fitz.PDF_ENCRYPT_AES_256, user_pw="test-password")
		with self.assertRaises(frappe.ValidationError):
			execute(
				"esign_upload_pdf",
				{"file_name": "encrypted.pdf", "content_base64": base64.b64encode(content).decode()},
			)

	def test_nested_lifecycle_and_signature_inputs_are_rejected(self):
		for data in (
			{"status": "Completed"},
			{"signers": [{"signer_name": "Test", "signer_email": "test@example.test", "token": "forged"}]},
		):
			with self.assertRaises(frappe.ValidationError):
				execute("esign_create_draft", {"data": data, "pdf_file": "/private/files/test.pdf"})

	def test_template_lifecycle_through_mcp(self):
		source = make_template()
		created = execute(
			"esign_create_template",
			{
				"data": {
					"title": "MCP lifecycle",
					"pdf_file": source.pdf_file,
					"signer_roles": [{"role_key": "client", "role_label": "Client"}],
				}
			},
		)
		name = created["name"]
		execute("esign_save_template_fields", {"name": name, "fields": guide()["example"]["fields"]})
		published = execute("esign_publish_template", {"name": name})
		self.assertEqual(published["status"], "Active")
		self.assertEqual(published["version_count"], 1)
		copy = execute("esign_duplicate_template", {"name": name})
		self.assertEqual(copy["status"], "Draft")
		self.assertEqual(execute("esign_archive_template", {"name": name})["status"], "Archived")

	def test_file_permissions_checked_before_reading_bytes(self):
		from unittest.mock import MagicMock

		from nesscale_sign.mcp import files

		doc = MagicMock()
		doc.check_permission.side_effect = frappe.PermissionError
		with (
			patch.object(frappe.db, "get_value", return_value="private-file"),
			patch("frappe.get_doc", return_value=doc),
			patch.object(files, "read_file_content") as read,
		):
			with self.assertRaises(frappe.PermissionError):
				execute(
					"esign_download_file", {"file_url": "/private/files/secret.pdf", "include_content": True}
				)
			read.assert_not_called()

	def test_signing_inbox_does_not_return_bearer_token(self):
		with patch(
			"nesscale_sign.api.envelope.my_pending_signatures",
			return_value=[{"name": "ENV-TEST", "token": "secret-token"}],
		):
			result = execute("esign_my_pending_signatures", {})
		self.assertNotIn("secret-token", json.dumps(result))

	def test_all_registered_schemas_and_native_hooks(self):
		from jsonschema import Draft7Validator

		from nesscale_sign import hooks

		registered = {path.split(".")[-2] for path in hooks.assistant_tools}
		self.assertEqual(registered, {spec["name"] for spec in definitions()})
		for spec in definitions():
			Draft7Validator.check_schema(spec["inputSchema"])
