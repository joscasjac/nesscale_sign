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

	def test_rich_content_variables_and_padding_render_as_literals(self):
		data = {
			"resolvedVariables": [{"key": "custom.project", "value": "Alpha & Beta"}],
			"pages": [
				{
					"blocks": [
						{
							"type": "Text",
							"text": "Project {{custom.project}}",
							"html": "<b>Project</b> {{custom.project}}",
							"x": 40,
							"y": 40,
							"width": 500,
							"height": 100,
							"padding": 10,
							"font_size": 16,
							"line_height": 1.5,
						}
					]
				}
			],
		}
		with fitz.open(stream=render_document(data), filetype="pdf") as pdf:
			self.assertIn("Project Alpha & Beta", pdf[0].get_text())
			self.assertNotIn("{{", pdf[0].get_text())
		data["resolvedVariables"] = []
		with self.assertRaises(frappe.ValidationError):
			render_document(data)

	def test_removed_video_blocks_and_bad_padding_are_rejected(self):
		base = {"type": "Text", "text": "Review", "x": 40, "y": 40, "width": 500, "height": 100}
		for change in ({"type": "Video link"}, {"padding": float("nan")}, {"padding": 80}):
			with self.assertRaises(frappe.ValidationError):
				render_document({"pages": [{"blocks": [{**base, **change}]}]})

	def test_document_settings_reject_unsafe_redirects_and_sender_injection(self):
		from nesscale_sign.services.mail_options import validate_document_settings

		for url in ("javascript:alert(1)", "http://example.test", "https://user:pass@example.test"):
			with self.assertRaises(frappe.ValidationError):
				validate_document_settings(frappe._dict(completion_redirect_url=url))
		with self.assertRaises(frappe.ValidationError):
			validate_document_settings(frappe._dict(email_from_name="Sender\nBcc: other@example.test"))
		validate_document_settings(
			frappe._dict(
				completion_redirect_url="https://example.test/thanks", completion_redirect_target="New tab"
			)
		)

	def test_rich_variables_cross_formatting_and_lists_keep_numbering(self):
		from nesscale_sign.services.document_variables import rich_paragraph

		markup = rich_paragraph(
			"<b>{{custom.</b>project}}<ol><li>First</li><li>Second</li></ol>",
			{"custom.project": "Alpha & Beta"},
		)
		self.assertIn("Alpha &amp; Beta", markup)
		self.assertNotIn("{{", markup)
		self.assertIn("1. First", markup)
		self.assertIn("2. Second", markup)

	def test_default_heading_paragraph_and_multiline_table_render(self):
		data = {
			"pages": [
				{
					"blocks": [
						{
							"type": "Text",
							"text": "Heading\nAdd text to your document.",
							"html": "<h2>Heading</h2><p>Add text to your document.</p>",
							"x": 38,
							"y": 46,
							"width": 519,
							"height": 94,
							"padding": 10,
							"font_size": 16,
							"line_height": 1.5,
						},
						{
							"type": "Table",
							"text": "",
							"cells": [["One\nTwo", "Three"], ["Four", "Five"]],
							"x": 38,
							"y": 160,
							"width": 519,
							"height": 150,
							"padding": 10,
							"font_size": 16,
							"line_height": 1.5,
						},
					]
				}
			]
		}
		with fitz.open(stream=render_document(data), filetype="pdf") as pdf:
			self.assertIn("Heading", pdf[0].get_text())
			self.assertIn("Two", pdf[0].get_text())

	def test_unsigned_revision_invalidates_links_and_keeps_original(self):
		from nesscale_sign.api.envelope import revise_unsigned
		from nesscale_sign.services.envelope_service import EnvelopeService
		from nesscale_sign.services.signing_service import SigningService

		env = make_envelope(make_template("Revision test").name, two_signers_single(), send=False)
		with patch("frappe.sendmail"):
			env = EnvelopeService(env.name).send()
		token = env.signers[0].token
		result = revise_unsigned(env.name)
		self.assertEqual(frappe.get_doc("NS Envelope", result["name"]).status, "Draft")
		self.assertEqual(frappe.get_doc("NS Envelope", env.name).status, "Voided")
		with self.assertRaises(frappe.PermissionError):
			SigningService(token)

	def test_pdf_combination_and_landscape_overlay_preserve_original(self):
		from nesscale_sign.api.builder import combine_pdfs, render
		from nesscale_sign.utils.files import read_file_content

		original = fitz.open()
		page = original.new_page(width=842, height=595)
		page.insert_text((300, 300), "Original landscape content")
		file = save_private_file("landscape.pdf", original.tobytes())
		original.close()
		combined = combine_pdfs([file.file_url, file.file_url])
		self.assertEqual(combined["page_count"], 2)
		data = {
			"pages": [
				{
					"blocks": [
						{
							"type": "Text",
							"text": "Added content",
							"x": 38,
							"y": 32,
							"width": 519,
							"height": 60,
							"padding": 10,
							"font_size": 16,
						}
					]
				}
			]
		}
		result = render(data, source_pdf=file.file_url)
		with fitz.open(stream=read_file_content(result["file_url"]), filetype="pdf") as pdf:
			self.assertEqual(round(pdf[0].rect.width), 842)
			self.assertIn("Original landscape content", pdf[0].get_text())
			self.assertIn("Added content", pdf[0].get_text())
