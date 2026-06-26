# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Email Template management API.

Surfaces the seeded default signing templates (and any others) for editing from
the SPA, and can restore the shipped defaults.
"""

import frappe

from nesscale_sign.api import load, require_manager
from nesscale_sign.email.seed import TEMPLATE_NAMES, seed_email_templates

DEFAULT_NAMES = set(TEMPLATE_NAMES.values())


@frappe.whitelist()
def list_email_templates():
	require_manager()
	rows = frappe.get_list(
		"Email Template",
		fields=["name", "subject", "use_html", "modified"],
		order_by="name asc",
		limit_page_length=0,
	)
	for row in rows:
		row["is_default"] = row["name"] in DEFAULT_NAMES
	return rows


@frappe.whitelist()
def get_email_template(name: str):
	require_manager()
	doc = frappe.get_doc("Email Template", name)
	return {
		"name": doc.name,
		"subject": doc.subject,
		"use_html": doc.use_html,
		"response": doc.response,
		"response_html": doc.response_html,
		"is_default": doc.name in DEFAULT_NAMES,
	}


@frappe.whitelist()
def save_email_template(data: dict | None = None):
	require_manager()
	data = load(data) or {}
	name = data.get("name")
	if name and frappe.db.exists("Email Template", name):
		doc = frappe.get_doc("Email Template", name)
	else:
		doc = frappe.new_doc("Email Template")
		doc.name = name
	doc.subject = data.get("subject")
	doc.use_html = 1 if data.get("use_html") else 0
	if doc.use_html:
		doc.response_html = data.get("response_html") or data.get("response")
	else:
		doc.response = data.get("response") or data.get("response_html")
	doc.save(ignore_permissions=True)
	return {"name": doc.name}


SAMPLE_CONTEXT = {
	"brand": "Nesscale Sign",
	"title": "Service Agreement",
	"signer_name": "Jane Doe",
	"role": "Client",
	"sign_url": "https://example.com/sign/preview",
	"expires_on": "31 Dec 2026",
	"reason": "",
}


@frappe.whitelist()
def preview(data: dict | None = None):
	"""Render a template body + subject with sample data for the editor preview."""
	require_manager()
	data = load(data) or {}
	try:
		# nosemgrep: frappe-ssti — manager-only template authoring (require_manager
		# above), mirroring Frappe's own Email Template editor. Rendered against a
		# fixed SAMPLE_CONTEXT, never returned to or executed for guests.
		subject = frappe.render_template(data.get("subject") or "", SAMPLE_CONTEXT)
		message = frappe.render_template(data.get("response") or "", SAMPLE_CONTEXT)
	except Exception as exc:
		return {"subject": "", "message": f"<p style='color:#dc2626'>Template error: {exc}</p>"}
	return {"subject": subject, "message": message}


@frappe.whitelist()
def restore_defaults():
	"""Delete and re-create the shipped default signing templates."""
	require_manager()
	for name in DEFAULT_NAMES:
		if frappe.db.exists("Email Template", name):
			frappe.delete_doc("Email Template", name, ignore_permissions=True, force=True)
	seed_email_templates()
	return {"restored": len(DEFAULT_NAMES)}
