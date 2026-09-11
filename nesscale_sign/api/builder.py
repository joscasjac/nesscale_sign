"""Authenticated document-builder PDF generation."""

import frappe

from nesscale_sign.api import load
from nesscale_sign.services.builder_service import render_document
from nesscale_sign.utils.files import save_private_file


@frappe.whitelist()
def render(data):
	frappe.has_permission("NS Envelope", "create", throw=True)
	content = render_document(load(data))
	file = save_private_file("built-document.pdf", content)
	return {"file_url": file.file_url}
