"""Private, bounded file transfer for MCP clients (no URL fetching)."""

import base64
import binascii
import hashlib
import io
import re

import frappe

from nesscale_sign.utils.files import read_authorized_pdf, read_file_content, save_private_file, validate_pdf


def _decode(file_name, content_base64, extension, limit):
	frappe.has_permission("NS Envelope", "create", throw=True)
	frappe.has_permission("File", "create", throw=True)
	# Do not accept a path, URL, control characters, or a misleading extension.
	if not re.fullmatch(r"[\w .()-]{1,140}\.(?:" + extension + r")", file_name, re.IGNORECASE):
		frappe.throw("Use a simple filename with the correct extension, without directories.")
	if len(content_base64) > 4 * ((limit + 2) // 3):
		frappe.throw("File exceeds the upload size limit.")
	try:
		content = base64.b64decode(content_base64, validate=True)
	except ValueError, binascii.Error:
		frappe.throw("Provide valid base64 file bytes, without a data URL prefix.")
	if not content or len(content) > limit:
		frappe.throw("File is empty or exceeds the upload size limit.")
	return content


def _metadata(file_url, content):
	return {"file_url": file_url, "size_bytes": len(content), "sha256": hashlib.sha256(content).hexdigest()}


def upload_pdf(file_name, content_base64):
	content = _decode(file_name, content_base64, "pdf", 15 * 1024 * 1024)
	validate_pdf(content)
	file = save_private_file(file_name, content)
	return {"file_name": file.file_name, "file_id": file.name, **_pdf_metadata(file.file_url, content)}


def upload_image(file_name, content_base64):
	from PIL import Image

	content = _decode(file_name, content_base64, "png|jpg|jpeg", 5 * 1024 * 1024)
	try:
		with Image.open(io.BytesIO(content)) as image:
			expected = "PNG" if file_name.lower().endswith(".png") else "JPEG"
			if image.format != expected or image.width * image.height > 16_000_000:
				frappe.throw("Use a PNG/JPEG matching the filename, under 16 million pixels.")
			image.verify()
	except OSError, ValueError, Image.DecompressionBombError:
		frappe.throw("The image could not be read.")
	file = save_private_file(file_name, content)
	return {"file_name": file.file_name, "file_id": file.name, **_metadata(file.file_url, content)}


def _pdf_metadata(file_url, content):
	import fitz

	with fitz.open(stream=content, filetype="pdf") as pdf:
		return {
			**_metadata(file_url, content),
			"page_count": pdf.page_count,
			"pages": [
				{"page": i + 1, "width": page.rect.width, "height": page.rect.height}
				for i, page in enumerate(pdf)
			],
		}


def inspect_pdf(file_url):
	return _pdf_metadata(file_url, read_authorized_pdf(file_url))


def _chunk(file_url, content, offset=0, length=65536, include_content=False):
	if offset > len(content):
		frappe.throw("Offset is beyond the end of the file.")
	result = _metadata(file_url, content)
	if include_content:
		end = min(offset + length, len(content))
		result.update(
			content_base64=base64.b64encode(content[offset:end]).decode("ascii"),
			offset=offset,
			next_offset=end,
			eof=end == len(content),
		)
	return result


def download_file(file_url, **options):
	name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not name:
		frappe.throw("File not found.")
	file = frappe.get_doc("File", name)
	file.check_permission("read")
	return {
		"file_name": file.file_name,
		"file_id": file.name,
		**_chunk(file_url, read_file_content(file_url), **options),
	}


def download_document(name, artifact, **options):
	doc = frappe.get_doc("NS Envelope", name)
	doc.check_permission("read")
	field = {"source": "source_pdf", "signed": "signed_pdf", "certificate": "certificate_pdf"}[artifact]
	url = doc.get(field)
	if not url:
		frappe.throw("The requested document artifact is not available yet.")
	# Parent access authorizes its artifacts, as in the existing download endpoints.
	result = _chunk(url, read_file_content(url), **options)
	if artifact == "signed" and options.get("include_content") and options.get("offset", 0) == 0:
		from nesscale_sign.services.audit_service import AuditService

		AuditService(name).log("Downloaded", details="Signed PDF downloaded through MCP")
	return {"name": name, "artifact": artifact, "file_name": name + "-" + artifact + ".pdf", **result}
