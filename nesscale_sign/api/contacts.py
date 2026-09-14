"""Minimal, permission-checked contact snapshots for document preparation."""

import frappe


@frappe.whitelist()
def search_contacts(query=""):
	query = str(query or "").strip()[:100]
	return frappe.get_list(
		"Contact",
		filters={"full_name": ["like", "%" + query + "%"]},
		fields=["name", "full_name", "email_id"],
		order_by="full_name asc",
		limit_page_length=20,
	)


@frappe.whitelist()
def get_contact_prefill(name):
	contact = frappe.get_doc("Contact", name)
	contact.check_permission("read")
	return {"full_name": contact.full_name or contact.first_name, "email_id": contact.email_id or ""}


@frappe.whitelist()
def create_contact(full_name, email_id):
	full_name = str(full_name or "").strip()
	if not full_name or len(full_name) > 140:
		frappe.throw("Enter a contact name under 140 characters.")
	frappe.utils.validate_email_address(email_id, throw=True)
	parts = full_name.split(" ", 1)
	doc = frappe.get_doc(
		{
			"doctype": "Contact",
			"first_name": parts[0],
			"last_name": parts[1] if len(parts) > 1 else "",
			"email_ids": [{"email_id": email_id, "is_primary": 1}],
		}
	)
	doc.insert()
	return {"name": doc.name, "full_name": doc.full_name, "email_id": doc.email_id}
