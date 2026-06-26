# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""DocType auto-creation, field/manual signer resolution, prefill, and reversal."""

import frappe
from frappe.tests.utils import FrappeTestCase

from nesscale_sign.services.envelope_service import EnvelopeService
from nesscale_sign.services.integration_service import IntegrationService
from nesscale_sign.tests.utils import make_template


def _auto_template(title, *, event="Save", manual_email="client@test.com", fields=None):
	tmpl = make_template(title, fields=fields)
	doc = frappe.get_doc("NS Template", tmpl.name)
	doc.auto_create = 1
	doc.trigger_doctype = "ToDo"
	doc.trigger_event = event
	doc.trigger_auto_send = 1
	doc.signer_roles[0].manual_email = manual_email
	doc.signer_roles[0].source_name_field = "description"
	doc.save()
	return doc


class TestAutoCreate(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_save_event_creates_and_sends(self):
		# "Save" fires on the first save (insert), so the envelope is created then.
		t = _auto_template("Auto Save")
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Acme Co Ltd"}).insert()
		envs = frappe.get_all("NS Envelope", filters={"template": t.name}, pluck="name")
		self.assertEqual(len(envs), 1)
		env = frappe.get_doc("NS Envelope", envs[0])
		self.assertEqual(env.status, "Sent")
		self.assertEqual(env.signers[0].signer_email, "client@test.com")
		self.assertEqual(env.signers[0].signer_name, "Acme Co Ltd")
		# Idempotent
		todo.description = "again"
		todo.save()
		self.assertEqual(frappe.db.count("NS Envelope", {"template": t.name}), 1)

	def test_blank_email_stays_draft(self):
		t = _auto_template("Auto Draft", manual_email="")  # no email -> can't resolve
		todo = frappe.get_doc({"doctype": "ToDo", "description": "X"}).insert()
		todo.description = "Y"
		todo.save()
		env = frappe.get_doc("NS Envelope", frappe.get_all("NS Envelope", filters={"template": t.name}, pluck="name")[0])
		self.assertEqual(env.status, "Draft")


class TestPrefill(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_field_prefilled_from_document(self):
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Prefill me"}).insert()
		tmpl = make_template(
			"Prefill",
			fields=[{
				"field_type": "Text", "label": "D", "signer_role": "signer", "page": 1,
				"pos_x": 0.1, "pos_y": 0.2, "width": 0.3, "height": 0.04, "mapping_key": "description",
			}],
		)
		env = EnvelopeService.create_from_template(
			tmpl.name,
			{"title": "P", "signers": [{"signer_name": "S", "signer_email": "s@test.com", "role_key": "signer"}],
			 "source_doctype": "ToDo", "source_name": todo.name},
		)
		row = frappe.get_all("NS Envelope Field", filters={"envelope": env.name}, fields=["value", "read_only"])[0]
		self.assertEqual(row.value, "Prefill me")
		self.assertTrue(row.read_only)


class TestReversal(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")

	def test_delete_reference_voids_envelope(self):
		t = _auto_template("Reversal Del")
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Quote"}).insert()
		todo.description = "Quote v2"
		todo.save()
		env_name = frappe.get_all("NS Envelope", filters={"template": t.name}, pluck="name")[0]
		self.assertEqual(frappe.db.get_value("NS Envelope", env_name, "status"), "Sent")

		frappe.delete_doc("ToDo", todo.name)  # on_trash -> reversal
		self.assertEqual(frappe.db.get_value("NS Envelope", env_name, "status"), "Voided")

	def test_cancel_reference_voids_envelope(self):
		t = _auto_template("Reversal Cancel")
		todo = frappe.get_doc({"doctype": "ToDo", "description": "Quote"}).insert()
		todo.description = "Quote v2"
		todo.save()
		env_name = frappe.get_all("NS Envelope", filters={"template": t.name}, pluck="name")[0]
		# ToDo is not submittable, so simulate the cancel event directly.
		IntegrationService.handle_doc_event(frappe.get_doc("ToDo", todo.name), "on_cancel")
		self.assertEqual(frappe.db.get_value("NS Envelope", env_name, "status"), "Voided")
