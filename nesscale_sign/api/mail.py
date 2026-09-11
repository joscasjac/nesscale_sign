"""Email template discovery for authenticated document preparation."""

import frappe


@frappe.whitelist()
def list_templates():
	return frappe.get_list("Email Template", fields=["name", "subject"], limit_page_length=100)


@frappe.whitelist()
def create_template(name, subject, body):
	if not str(name).strip() or len(str(subject)) > 200 or len(str(body)) > 20000:
		frappe.throw("Use a name, a subject under 200 characters and a body under 20,000 characters.")
	from nesscale_sign.services.mail_options import plain_message

	doc = frappe.get_doc(
		{
			"doctype": "Email Template",
			"name": name,
			"subject": subject,
			"use_html": 1,
			"response_html": plain_message(body),
		}
	)
	doc.insert()
	return {"name": doc.name, "subject": doc.subject}


@frappe.whitelist()
def list_attachments(names="[]"):
	import json

	from nesscale_sign.services.mail_options import attachment_docs

	attachment_docs(names, check_permission=True)
	return [
		{"name": name, "file_name": frappe.db.get_value("File", name, "file_name")}
		for name in json.loads(names)
	]
