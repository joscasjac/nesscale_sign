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
