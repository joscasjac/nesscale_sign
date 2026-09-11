# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""API-layer tests: exercise the thin whitelisted endpoints end to end."""

import frappe
from frappe.tests.utils import FrappeTestCase

from nesscale_sign.api import dashboard, envelope, signing, template
from nesscale_sign.tests.utils import make_private_pdf, make_template, signature_payload


class TestTemplateApi(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_create_and_get(self):
		created = template.create_template({"title": "API Tmpl", "pdf_file": make_private_pdf("api.pdf")})
		res = template.get_template(created["name"])
		self.assertEqual(res["template"]["title"], "API Tmpl")
		self.assertEqual(res["template"]["page_count"], 2)

	def test_save_fields_and_publish(self):
		created = template.create_template({"title": "API Pub", "pdf_file": make_private_pdf("apipub.pdf")})
		template.save_template_roles(created["name"], [{"role_label": "Signer", "role_key": "signer"}])
		template.save_template_fields(
			created["name"],
			[
				{
					"field_type": "Text",
					"label": "N",
					"signer_role": "signer",
					"page": 1,
					"pos_x": 0.1,
					"pos_y": 0.2,
					"width": 0.2,
					"height": 0.04,
				},
			],
		)
		published = template.publish_template(created["name"])
		self.assertEqual(published["status"], "Active")


class TestEnvelopeApi(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.tmpl = make_template("Env API Tmpl")

	def test_create_send_and_signing_roundtrip(self):
		env = envelope.create_from_template(
			self.tmpl.name,
			{
				"title": "API Env",
				"signers": [{"signer_name": "Z", "signer_email": "z@test.com", "role_key": "signer"}],
			},
		)
		envelope.send_envelope(env["name"])

		got = envelope.get_envelope(env["name"])
		self.assertEqual(got["envelope"]["status"], "Sent")
		self.assertNotIn("token", got["envelope"]["signers"][0])
		token = frappe.get_doc("NS Envelope", env["name"]).signers[0].token
		self.assertEqual(len(token), 40)

		# Public signing endpoints (guest-style) by token.
		ctx = signing.get_context(token)
		self.assertTrue(ctx["signer"]["can_sign"])
		values = {f["field_key"]: "Tester" for f in ctx["fields"] if f["field_type"] == "Text"}
		result = signing.submit(token, values, signature_payload(), consent=True)
		self.assertEqual(result["status"], "processing")
		from nesscale_sign.services.finalization import finalize_envelope

		finalize_envelope(env["name"] if isinstance(env, dict) else env.name)

		final = envelope.get_envelope(env["name"])
		self.assertEqual(final["envelope"]["status"], "Completed")
		self.assertTrue(final["envelope"]["signed_pdf"])

	def test_audit_endpoint_reports_integrity(self):
		env = envelope.create_from_template(
			self.tmpl.name,
			{
				"title": "Audit API",
				"signers": [{"signer_name": "Z", "signer_email": "z@test.com", "role_key": "signer"}],
			},
		)
		audit = envelope.get_audit(env["name"])
		self.assertIn("integrity", audit)
		self.assertTrue(audit["integrity"]["valid"])


class TestDashboardApi(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_stats_shape(self):
		stats = dashboard.get_stats()
		self.assertIn("counts", stats)
		self.assertIn("completion_rate", stats)
		self.assertIn("awaiting_me", stats)
