"""Authenticated document-builder PDF generation."""

import frappe

from nesscale_sign.api import load
from nesscale_sign.services.builder_service import render_document
from nesscale_sign.utils.files import save_private_file


@frappe.whitelist()
def render(data, source_pdf=None):
	frappe.has_permission("NS Envelope", "create", throw=True)
	data = load(data)
	if source_pdf:
		import fitz

		from nesscale_sign.utils.files import read_authorized_pdf

		original = read_authorized_pdf(source_pdf)
		with fitz.open(stream=original, filetype="pdf") as source:
			if len(data.get("pages", [])) != source.page_count:
				frappe.throw("The builder pages must match the uploaded PDF.")
			overlay_bytes = render_document(data, max_pages=100, page_sizes=[(595,595*page.rect.height/page.rect.width) for page in source])
			with fitz.open(stream=overlay_bytes, filetype="pdf") as overlay:
				for i, page in enumerate(source):
					if data["pages"][i].get("blocks"):
						page.show_pdf_page(page.rect, overlay, i, keep_proportion=False)
			content = source.tobytes()
	else:
		content = render_document(data)
	file = save_private_file("built-document.pdf", content)
	return {"file_url": file.file_url}


@frappe.whitelist()
def combine_pdfs(urls):
	import fitz

	from nesscale_sign.utils.files import read_authorized_pdf

	frappe.has_permission("NS Envelope", "create", throw=True)
	urls = load(urls)
	if not isinstance(urls, list) or not 1 <= len(urls) <= 10:
		frappe.throw("Choose between 1 and 10 PDFs.")
	combined = fitz.open()
	total = 0
	try:
		for url in urls:
			content = read_authorized_pdf(url)
			total += len(content)
			if total > 15 * 1024 * 1024:
				frappe.throw("PDFs must total 15 MB or less.")
			with fitz.open(stream=content, filetype="pdf") as pdf:
				if combined.page_count + pdf.page_count > 100:
					frappe.throw("Use at most 100 PDF pages.")
				combined.insert_pdf(pdf)
		file = save_private_file("combined-document.pdf", combined.tobytes())
		return {"file_url": file.file_url, "page_count": combined.page_count}
	finally:
		combined.close()
