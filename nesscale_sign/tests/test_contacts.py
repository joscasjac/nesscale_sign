"""Contact disclosures and editable-date validation."""

import frappe
from frappe.tests.utils import FrappeTestCase

from nesscale_sign.api.contacts import get_contact_prefill, search_contacts
from nesscale_sign.utils.security import validate_value


class TestContactPrefill(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.contact = frappe.get_doc(
			{
				"doctype": "Contact",
				"first_name": "Prefill",
				"last_name": "Regression",
				"email_ids": [{"email_id": "prefill@example.test", "is_primary": 1}],
			}
		).insert()

	def tearDown(self):
		frappe.set_user("Administrator")

	def test_prefill_discloses_only_name_and_primary_email(self):
		self.assertEqual(
			get_contact_prefill(self.contact.name),
			{
				"full_name": "Prefill Regression",
				"email_id": "prefill@example.test",
			},
		)
		self.assertTrue(any(c.name == self.contact.name for c in search_contacts("Prefill Regression")))

	def test_guest_cannot_search_or_fetch_contacts(self):
		frappe.set_user("Guest")
		with self.assertRaises(frappe.PermissionError):
			get_contact_prefill(self.contact.name)
		with self.assertRaises(frappe.PermissionError):
			search_contacts("Prefill")

	def test_editable_date_requires_real_iso_calendar_date(self):
		row = {"field_type": "Date"}
		self.assertEqual(validate_value(row, "2026-09-11"), "2026-09-11")
		for value in ["2026-02-30", "20260911", "11/09/2026", True]:
			with self.assertRaises(frappe.ValidationError):
				validate_value(row, value)
