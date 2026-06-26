# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""DocType auto-creation API endpoints."""

import frappe

from nesscale_sign.api import require_manager

TRIGGER_EVENTS = ["New", "Save", "Submit", "Cancel", "Value Change", "Days Before", "Days After"]


@frappe.whitelist()
def trigger_events():
	return TRIGGER_EVENTS


@frappe.whitelist()
def search_doctypes(txt: str | None = None):
	"""Normal DocTypes only — excludes child tables and single doctypes."""
	filters = [["istable", "=", 0], ["issingle", "=", 0]]
	if txt:
		filters.append(["name", "like", f"%{txt}%"])
	return frappe.get_all("DocType", filters=filters, pluck="name", order_by="name asc", limit_page_length=20)


@frappe.whitelist()
def get_doctype_fields(doctype: str):
	"""Mappable fields of a DocType for the signer/field mapping pickers."""
	if not doctype or not frappe.db.exists("DocType", doctype):
		return []
	meta = frappe.get_meta(doctype)
	mappable = {
		"Data", "Small Text", "Text", "Long Text", "Select", "Link", "Read Only",
		"Int", "Float", "Currency", "Date", "Datetime", "Phone", "Check", "Percent",
	}
	fields = [
		{
			"fieldname": f.fieldname,
			"label": f.label or f.fieldname,
			"fieldtype": f.fieldtype,
			"options": f.options,
		}
		for f in meta.fields
		if f.fieldtype in mappable and f.fieldname
	]
	# Standard fields worth mapping: the document owner (a User) is a natural
	# signer email source, alongside the record id.
	fields.insert(0, {"fieldname": "owner", "label": "Owner (Created By)", "fieldtype": "Link", "options": "User"})
	fields.insert(0, {"fieldname": "name", "label": "ID (name)", "fieldtype": "Data", "options": None})
	return fields
