# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Private file helpers.

Every artifact produced by Nesscale Sign (source PDFs, signatures, signed
output, certificates) is stored as a *private* File so that URLs are never
publicly guessable and access is mediated by permissions / signed tokens.
"""

import base64
import io
import os

import frappe
from PIL import Image


def save_private_file(
	file_name: str,
	content: bytes,
	*,
	attached_to_doctype: str | None = None,
	attached_to_name: str | None = None,
	attached_to_field: str | None = None,
) -> "frappe.Document":
	"""Persist bytes as a private File and return the File document."""
	file_doc = frappe.get_doc(
		{
			"doctype": "File",
			"file_name": file_name,
			"is_private": 1,
			"content": content,
			"attached_to_doctype": attached_to_doctype,
			"attached_to_name": attached_to_name,
			"attached_to_field": attached_to_field,
		}
	)
	file_doc.flags.ignore_permissions = True
	file_doc.insert(ignore_permissions=True)
	return file_doc


def save_base64_image(
	file_name: str,
	data_url: str,
	**kwargs,
) -> "frappe.Document":
	"""Save a base64 / data-URL encoded image as a private File."""
	if "," in data_url and data_url.strip().startswith("data:"):
		data_url = data_url.split(",", 1)[1]
	if not isinstance(data_url, str) or len(data_url) > 3_000_000:
		frappe.throw("Signature image is too large.")
	try:
		content = base64.b64decode(data_url, validate=True)
		with Image.open(io.BytesIO(content)) as image:
			if image.width * image.height > 4_000_000 or image.width < 2 or image.height < 2:
				frappe.throw("Invalid signature image size.")
			image.load()
			out = io.BytesIO()
			image.convert("RGBA").save(out, "PNG")
			content = out.getvalue()
	except ValueError, OSError:
		frappe.throw("Upload a valid signature image.")
	return save_private_file(file_name, content, **kwargs)


def read_file_content(file_url: str) -> bytes:
	"""Read the raw bytes for a File by its file_url, regardless of privacy.

	Always reads from disk in binary mode so PDFs are never accidentally
	text-decoded (``File.get_content`` may decode by extension). The resolved
	path is constrained to the site directory to prevent path traversal.
	"""
	if not file_url:
		raise frappe.ValidationError("Missing file url")
	file_name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if file_name:
		path = frappe.get_doc("File", file_name).get_full_path()
	else:
		path = get_file_path(file_url)
	path = _ensure_within_site(path)
	with open(path, "rb") as fh:  # nosemgrep: path is constrained to the site dir
		return fh.read()


def get_file_path(file_url: str) -> str:
	site_path = frappe.get_site_path()
	# Strip any directory components — only the basename is trusted from an
	# unmatched file_url, which neutralises ``../`` traversal sequences.
	if file_url.startswith("/private/"):
		return os.path.join(site_path, "private", "files", os.path.basename(file_url))
	return os.path.join(site_path, "public", "files", os.path.basename(file_url))


def _ensure_within_site(path: str) -> str:
	"""Reject any resolved path that escapes the site directory."""
	site_root = os.path.realpath(frappe.get_site_path())
	resolved = os.path.realpath(path)
	if not (resolved == site_root or resolved.startswith(site_root + os.sep)):
		frappe.throw(frappe._("Invalid file path"), frappe.PermissionError)
	return resolved


def read_authorized_pdf(file_url):
	name = frappe.db.get_value("File", {"file_url": file_url}, "name")
	if not name:
		frappe.throw("Upload a PDF first.")
	doc = frappe.get_doc("File", name)
	doc.check_permission("read")
	content = read_file_content(file_url)
	validate_pdf(content)
	return content


def validate_pdf(content):
	import fitz

	if len(content) > 15 * 1024 * 1024:
		frappe.throw("PDFs must be 15 MB or smaller.")
	try:
		with fitz.open(stream=content, filetype="pdf") as pdf:
			if pdf.needs_pass or not 1 <= pdf.page_count <= 100:
				frappe.throw("Use an unencrypted PDF with 1-100 pages.")
			if any(list(p.widgets() or []) for p in pdf):
				frappe.throw("Flatten existing PDF form fields before uploading.")
	except RuntimeError, ValueError:
		frappe.throw("This file could not be read as a PDF.")
