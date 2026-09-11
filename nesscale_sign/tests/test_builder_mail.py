"""Document generation and invitation regression coverage."""

import json
from unittest.mock import patch

import fitz
import frappe
from frappe.tests.utils import FrappeTestCase

from nesscale_sign.services.builder_service import render_document
from nesscale_sign.services.mail_options import attachment_docs
from nesscale_sign.services.notification_service import NotificationService
from nesscale_sign.tests.utils import make_envelope, make_template, two_signers_single
from nesscale_sign.utils.files import save_private_file


class TestBuilderMail(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_builder_renders_pages_and_escapes_markup(self):
		data = {
			"pages": [
				{
					"blocks": [
						{
							"type": "Heading",
							"text": "Agreement <review>",
							"x": 40,
							"y": 40,
							"width": 500,
							"height": 100,
							"font_size": 24,
						}
					]
				},
				{"blocks": []},
			]
		}
		with fitz.open(stream=render_document(data), filetype="pdf") as pdf:
			self.assertEqual(pdf.page_count, 2)
			self.assertIn("Agreement <review>", pdf[0].get_text())

	def test_builder_rejects_invalid_geometry_overflow_and_remote_images(self):
		block = {"type": "Text", "text": "word " * 1000, "x": 40, "y": 40, "width": 500, "height": 20}
		for changed in [{}, {"x": -1}, {"type": "Image", "image": "https://example.test/image.png"}]:
			with self.assertRaises(frappe.ValidationError):
				render_document({"pages": [{"blocks": [{**block, **changed}]}]})

	def test_invitation_uses_override_link_and_attachments(self):
		env = make_envelope(make_template("Invitation override test").name, two_signers_single())
		file = save_private_file("notes.txt", b"Supporting notes")
		env.email_subject = "Please review"
		env.email_message = "Hello\n<script>not HTML</script>"
		env.email_attachments = json.dumps([file.name])
		with patch("frappe.sendmail") as send:
			NotificationService(env).send_invitation(env.signers[0])
			args = send.call_args.kwargs
			self.assertEqual(args["subject"], "Please review")
			self.assertIn("&lt;script&gt;", args["message"])
			self.assertIn("/sign/" + env.signers[0].token, args["message"])
			self.assertEqual(args["attachments"][0]["fcontent"], b"Supporting notes")

	def test_attachment_permissions_and_count_are_enforced(self):
		file = save_private_file("private-notes.txt", b"Private notes")
		with self.assertRaises(frappe.ValidationError):
			attachment_docs(json.dumps([file.name] * 6), True)
		try:
			frappe.set_user("Guest")
			with self.assertRaises(frappe.PermissionError):
				attachment_docs(json.dumps([file.name]), True)
		finally:
			frappe.set_user("Administrator")

	def test_built_draft_saves_and_reopens_without_recipients(self):
		from nesscale_sign.api.builder import render
		from nesscale_sign.api.envelope import create_adhoc, get_envelope, update_envelope

		data = {"pages": [{"blocks": []}]}
		pdf = render(data)
		env = create_adhoc(
			{
				"title": "Builder draft",
				"pdf_file": pdf["file_url"],
				"builder_json": json.dumps(data),
				"signers": [],
				"fields": [],
			}
		)
		reopened = get_envelope(env["name"])
		self.assertEqual(json.loads(reopened["envelope"]["builder_json"]), data)
		update_envelope(env["name"], {"email_subject": "Custom subject", "email_message": "Custom body"})
		self.assertEqual(get_envelope(env["name"])["envelope"]["email_message"], "Custom body")

	def test_reusable_email_template_is_rendered(self):
		from nesscale_sign.api.mail import create_template

		name = "Builder email " + frappe.generate_hash(length=8)
		created = create_template(name, "Review {{ title }}", "Hello {{ signer_name }}")
		env = make_envelope(make_template("Reusable email").name, two_signers_single())
		env.email_template = created["name"]
		env.email_subject = ""
		with patch("frappe.sendmail") as send:
			NotificationService(env).send_invitation(env.signers[0])
			self.assertIn(env.title, send.call_args.kwargs["subject"])
			self.assertIn(env.signers[0].signer_name, send.call_args.kwargs["message"])
