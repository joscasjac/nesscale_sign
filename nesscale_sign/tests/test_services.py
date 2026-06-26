# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Service-layer tests: templates, PDF engine, audit chain, permissions."""

import frappe
from frappe.tests.utils import FrappeTestCase

from nesscale_sign.services import pdf_service
from nesscale_sign.services.audit_service import AuditService
from nesscale_sign.services.template_service import TemplateService
from nesscale_sign.tests.utils import make_envelope, make_pdf, make_template, two_signers_single


class TestTemplateService(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_create_sets_page_count(self):
		tmpl = make_template("Pages Tmpl", publish=False)
		self.assertEqual(tmpl.page_count, 2)

	def test_publish_requires_pdf_and_roles(self):
		doc = frappe.new_doc("NS Template")
		doc.title = "Bare"
		doc.insert()
		with self.assertRaises(frappe.ValidationError):
			TemplateService(doc.name).publish()

	def test_publish_creates_version(self):
		tmpl = make_template("Versioned")
		tmpl.reload()
		self.assertEqual(tmpl.status, "Active")
		self.assertEqual(tmpl.version_count, 1)
		self.assertTrue(tmpl.current_version)

	def test_fields_persist(self):
		tmpl = make_template("Fields Tmpl")
		fields = TemplateService(tmpl.name).get_fields()
		self.assertEqual(len(fields), 2)


class TestPdfEngine(FrappeTestCase):
	def test_page_count(self):
		self.assertEqual(pdf_service.get_page_count(make_pdf(3)), 3)

	def test_overlay_preserves_pages_and_flattens(self):
		src = make_pdf(2)
		fields = [
			{"field_key": "t1", "field_type": "Text", "value": "Hello", "page": 1,
			 "pos_x": 0.1, "pos_y": 0.2, "width": 0.3, "height": 0.04, "font_size": 12},
			{"field_key": "c1", "field_type": "Checkbox", "value": "1", "page": 2,
			 "pos_x": 0.1, "pos_y": 0.2, "width": 0.03, "height": 0.02},
		]
		out = pdf_service.generate_filled_pdf(src, fields, {})
		self.assertEqual(pdf_service.get_page_count(out), 2)
		# No AcroForm widgets => flattened.
		import fitz

		with fitz.open(stream=out, filetype="pdf") as doc:
			widgets = list(doc[0].widgets() or [])
			self.assertEqual(len(widgets), 0)


class TestAuditChain(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.tmpl = make_template("Audit Tmpl")

	def test_chain_valid_after_events(self):
		env = make_envelope(self.tmpl.name, two_signers_single(), send=True)
		svc = AuditService(env.name)
		svc.log("Viewed", signer_email="solo@test.com")
		result = svc.verify()
		self.assertTrue(result["valid"])
		self.assertGreaterEqual(result["count"], 2)

	def test_tamper_breaks_chain(self):
		env = make_envelope(self.tmpl.name, two_signers_single(), send=True)
		svc = AuditService(env.name)
		svc.log("Viewed", signer_email="solo@test.com")
		# Tamper with a middle row directly in the DB.
		rows = frappe.get_all("NS Audit Log", filters={"envelope": env.name},
			order_by="creation asc", pluck="name")
		frappe.db.set_value("NS Audit Log", rows[0], "details", "TAMPERED", update_modified=False)
		result = svc.verify()
		self.assertFalse(result["valid"])


class TestPermissions(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_user_query_condition_scopes_to_owner(self):
		from nesscale_sign.permissions.ns_permissions import envelope_query_conditions

		cond = envelope_query_conditions("some-user@test.com")
		self.assertIn("tabNS Envelope", cond)
		self.assertIn("owner", cond)

	def test_manager_sees_all(self):
		from nesscale_sign.permissions.ns_permissions import envelope_query_conditions

		self.assertEqual(envelope_query_conditions("Administrator"), "")
