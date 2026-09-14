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
