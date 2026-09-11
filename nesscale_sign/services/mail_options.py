"""Invitation overrides and bounded, permission-checked attachments."""

import json
from html import escape

import frappe

from nesscale_sign.utils.files import read_file_content


def plain_message(body):
	return "<p>" + escape(str(body or "")).replace("\n", "<br/>") + "</p>"


def attachment_docs(value, check_permission=False):
	try:
		ids = json.loads(value or "[]") if isinstance(value, str) else (value or [])
	except ValueError, TypeError:
		frappe.throw("Invalid email attachments.")
	if not isinstance(ids, list) or len(ids) > 5 or any(not isinstance(i, str) for i in ids):
		frappe.throw("Choose at most five email attachments.")
	docs, total = [], 0
	for name in ids:
		doc = frappe.get_doc("File", name)
		if check_permission:
			doc.check_permission("read")
		if not doc.is_private or not (doc.file_url or "").startswith("/private/files/"):
			frappe.throw("Email attachments must be private uploaded files.")
		content = read_file_content(doc.file_url)
		total += len(content)
		if total > 10 * 1024 * 1024:
			frappe.throw("Email attachments must total 10 MB or less.")
		docs.append({"fname": doc.file_name, "fcontent": content})
	return docs


def validate_options(doc):
	if len(doc.email_subject or "") > 200 or any(c in (doc.email_subject or "") for c in "\r\n"):
		frappe.throw("Use a one-line email subject under 200 characters.")
	if len(doc.email_message or "") > 20000:
		frappe.throw("Email body must be under 20,000 characters.")
	if doc.get("email_template"):
		frappe.get_doc("Email Template", doc.email_template).check_permission("read")
	attachment_docs(doc.get("email_attachments"), check_permission=True)
	if doc.get("builder_json") and len(doc.builder_json) > 10_000_000:
		frappe.throw("Document content is too large.")
