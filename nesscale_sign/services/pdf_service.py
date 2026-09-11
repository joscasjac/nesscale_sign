# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""PDF engine: metrics, field overlay, signature embedding, flattening and the
tamper-evident audit certificate.

Design notes
------------
* Field coordinates are stored normalised (0..1) against page width/height with
  a **top-left** origin — identical to PDF.js / the browser designer — so the
  same numbers drive both the on-screen designer and the server-side render.
* Values and signatures are drawn directly onto the page content stream. The
  output therefore contains **no AcroForm widgets**: it is inherently flat and
  cannot be re-edited in a PDF form editor.
* A separate completion certificate records signers, signatures and the audit
  trail. An optional PKI seal provides cryptographic integrity.
"""

import io
from datetime import UTC

import fitz  # PyMuPDF
import frappe

from nesscale_sign.utils.constants import SIGNATURE_FIELD_TYPES

_FONT_MAP = {
	"helvetica": "helv",
	"arial": "helv",
	"times": "tiro",
	"times new roman": "tiro",
	"courier": "cour",
	"mono": "cour",
}


def _fitz_font(font_family: str | None) -> str:
	return _FONT_MAP.get((font_family or "").strip().lower(), "helv")


def get_page_metrics(pdf_bytes: bytes) -> list[dict]:
	"""Return per-page width/height in PDF points."""
	metrics = []
	with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
		for index, page in enumerate(doc):
			rect = page.rect
			metrics.append({"page": index + 1, "width": rect.width, "height": rect.height})
	return metrics


def get_page_count(pdf_bytes: bytes) -> int:
	with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
		return doc.page_count


def _rect_for_field(page, field: dict) -> "fitz.Rect":
	pw, ph = page.rect.width, page.rect.height
	x0 = float(field.get("pos_x") or 0) * pw
	y0 = float(field.get("pos_y") or 0) * ph
	x1 = x0 + float(field.get("width") or 0) * pw
	y1 = y0 + float(field.get("height") or 0) * ph
	return fitz.Rect(x0, y0, x1, y1)


def _draw_text(page, rect, text, field):
	font_size = float(field.get("font_size") or 12)
	fontname = _fitz_font(field.get("font_family"))
	# Auto-shrink until the text fits the box (insert_textbox returns the unused
	# vertical space; a negative value means overflow).
	size = font_size
	while size >= 5:
		rc = page.insert_textbox(
			rect,
			str(text),
			fontsize=size,
			fontname=fontname,
			color=(0, 0, 0),
			align=fitz.TEXT_ALIGN_LEFT,
		)
		if rc >= 0:
			return
		size -= 1
	# Last resort: draw clipped at the smallest size.
	page.insert_textbox(rect, str(text), fontsize=5, fontname=fontname, color=(0, 0, 0))


def _draw_checkbox(page, rect, checked):
	page.draw_rect(rect, color=(0.2, 0.2, 0.2), width=0.8)
	if str(checked).lower() in ("1", "true", "yes", "on", "checked"):
		page.draw_line(rect.tl, rect.br, color=(0, 0, 0), width=1.4)
		page.draw_line(rect.bl, rect.tr, color=(0, 0, 0), width=1.4)


def _draw_image(page, rect, image_bytes):
	page.insert_image(rect, stream=image_bytes, keep_proportion=True, overlay=True)


def generate_filled_pdf(
	source_pdf_bytes: bytes,
	fields: list[dict],
	signature_images: dict[str, bytes] | None = None,
) -> bytes:
	"""Overlay all field values/signatures onto the source PDF and flatten.

	``signature_images`` maps a field's ``field_key`` to the raw image bytes for
	signature/initial/stamp fields.
	"""
	signature_images = signature_images or {}
	doc = fitz.open(stream=source_pdf_bytes, filetype="pdf")
	try:
		by_page: dict[int, list[dict]] = {}
		for field in fields:
			by_page.setdefault(int(field.get("page") or 1), []).append(field)

		for page_no, page_fields in by_page.items():
			if page_no < 1 or page_no > doc.page_count:
				continue
			page = doc[page_no - 1]
			for field in page_fields:
				rect = _rect_for_field(page, field)
				ftype = field.get("field_type")
				value = field.get("value")
				if ftype in SIGNATURE_FIELD_TYPES:
					img = signature_images.get(field.get("field_key"))
					if img:
						_draw_image(page, rect, img)
				elif ftype == "Checkbox":
					_draw_checkbox(page, rect, value)
				elif ftype == "Label":
					_draw_text(page, rect, field.get("label") or value or "", field)
				elif value not in (None, ""):
					_draw_text(page, rect, value, field)

		# Mark document as final in metadata.
		doc.set_metadata(
			{**(doc.metadata or {}), "producer": "Open E-Sign ERPNext", "title": "Signed Document"}
		)
		out = doc.tobytes(garbage=4, deflate=True)
		return out
	finally:
		doc.close()


def build_certificate(envelope: "frappe.Document", audit_rows: list[dict], chain: dict) -> bytes:
	"""Completion evidence with captured signatures; distinct from a PKI seal."""
	from reportlab.lib import colors
	from reportlab.lib.pagesizes import A4
	from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
	from reportlab.lib.units import mm
	from reportlab.platypus import (
		Image,
		KeepTogether,
		Paragraph,
		SimpleDocTemplate,
		Spacer,
		Table,
		TableStyle,
	)

	from nesscale_sign.utils import files

	buffer = io.BytesIO()
	doc = SimpleDocTemplate(
		buffer,
		pagesize=A4,
		leftMargin=18 * mm,
		rightMargin=18 * mm,
		topMargin=18 * mm,
		bottomMargin=18 * mm,
		title="Certificate of Completion",
	)
	styles = getSampleStyleSheet()
	h1 = ParagraphStyle(
		"certificate-title",
		parent=styles["Heading1"],
		fontSize=25,
		leading=30,
		textColor=colors.HexColor("#24362d"),
	)
	h2 = ParagraphStyle(
		"certificate-section", parent=styles["Heading2"], fontSize=12, textColor=colors.HexColor("#255b45")
	)
	normal = ParagraphStyle(
		"certificate-body", parent=styles["Normal"], fontSize=9, leading=13, wordWrap="CJK"
	)
	small = ParagraphStyle(
		"certificate-small", parent=normal, fontSize=7.5, leading=10, textColor=colors.HexColor("#626963")
	)

	def text(value, style=normal):
		return Paragraph(frappe.utils.escape_html(str(value or "Not recorded")), style)

	def stamp(value):
		if not value:
			return "Not recorded"
		from datetime import timezone
		from zoneinfo import ZoneInfo

		instant = frappe.utils.get_datetime(value)
		if instant.tzinfo is None:
			instant = instant.replace(tzinfo=ZoneInfo(frappe.utils.get_system_timezone()))
		return instant.astimezone(UTC).strftime("%Y-%m-%d %H:%M:%S UTC")

	story = [
		text("OPEN E-SIGN ERPNext", small),
		Spacer(1, 9),
		text("Certificate of Completion", h1),
		Spacer(1, 10),
		text(envelope.title, h2),
		text(f"Reference: {envelope.name}"),
		text(f"Status: {envelope.status}"),
		text(f"Sent: {stamp(envelope.sent_on)}"),
		text(f"Completed: {stamp(envelope.completed_on)}"),
		text(f"Sender: {envelope.sender_name or ''} <{envelope.sender_email or ''}>"),
		Spacer(1, 18),
	]
	signatures = frappe.get_all(
		"NS Signature",
		filters={"envelope": envelope.name},
		fields=["signer_email", "signature_image", "signature_type"],
		order_by="creation asc",
		limit_page_length=0,
	)
	by_email = {row.signer_email: row for row in signatures}
	for signer in envelope.signers:
		left = [
			text(signer.signer_name, h2),
			text(signer.signer_email),
			Spacer(1, 6),
			text(f"Status: {signer.status}"),
			text(f"Viewed: {stamp(signer.viewed_on)}"),
			text(f"Signed: {stamp(signer.signed_on)}"),
			text(f"IP address: {signer.ip_address or 'Not recorded'}"),
			text(
				f"Access method: {signer.auth_method if signer.auth_method and signer.auth_method != 'None' else 'Email signing link'}",
				small,
			),
		]
		right = [text("Captured signature", small), Spacer(1, 8)]
		record = by_email.get(signer.signer_email)
		if record and record.signature_image:
			image = Image(io.BytesIO(files.read_file_content(record.signature_image)))
			scale = min(70 * mm / image.imageWidth, 25 * mm / image.imageHeight)
			image.drawWidth = image.imageWidth * scale
			image.drawHeight = image.imageHeight * scale
			image.hAlign = "LEFT"
			right.extend([image, Spacer(1, 8), text(f"Entry method: {record.signature_type}", small)])
		else:
			right.append(text("No signature image captured.", small))
		right.extend(
			[
				text(f"Electronic consent: {signer.consent_version or 'Not recorded'}", small),
				text(signer.consent_text or "Consent text not recorded", small),
			]
		)
		block = Table([[left, right]], colWidths=[87 * mm, 87 * mm])
		block.setStyle(
			TableStyle(
				[
					("VALIGN", (0, 0), (-1, -1), "TOP"),
					("LINEABOVE", (0, 0), (-1, 0), 0.7, colors.HexColor("#b6c5b8")),
					("TOPPADDING", (0, 0), (-1, -1), 12),
					("BOTTOMPADDING", (0, 0), (-1, -1), 12),
				]
			)
		)
		story.extend([KeepTogether([block]), Spacer(1, 10)])
	story.extend([text("Document integrity", h2)])
	for label, value in (
		("Original SHA-256", envelope.source_sha256),
		("Completed PDF SHA-256", envelope.signed_sha256),
		("PDF seal", envelope.seal_status),
	):
		story.append(text(f"{label}: {value or 'Not recorded'}", small))
	story.append(
		text(
			f"Audit integrity: {'Consistent' if chain.get('valid') else 'Broken'}; {chain.get('count', 0)} chained events.",
			small,
		)
	)
	story.extend([Spacer(1, 14), text("Audit Trail", h2)])
	audit_data = [[text(label, small) for label in ("Time", "Event", "Actor / details")]]
	for row in audit_rows:
		audit_data.append(
			[
				text(stamp(row.get("timestamp")), small),
				text(row.get("action"), small),
				text(
					f"{row.get('signer_email') or row.get('signer_name') or 'System'}: {row.get('details') or ''}",
					small,
				),
			]
		)
	table = Table(audit_data, colWidths=[47 * mm, 32 * mm, 95 * mm], repeatRows=1)
	table.setStyle(
		TableStyle(
			[
				("VALIGN", (0, 0), (-1, -1), "TOP"),
				("LINEBELOW", (0, 0), (-1, 0), 0.5, colors.HexColor("#b6c5b8")),
				("TOPPADDING", (0, 0), (-1, -1), 6),
				("BOTTOMPADDING", (0, 0), (-1, -1), 6),
			]
		)
	)
	story.extend(
		[
			table,
			Spacer(1, 14),
			text(
				"This completion record describes events recorded by Open E-Sign ERPNext. A signature image is not a cryptographic seal or independent proof of identity. Database audit hashes alone are not an independently trusted digital signature. Location is not inferred from an IP address.",
				small,
			),
		]
	)

	def footer(canvas, document):
		canvas.saveState()
		canvas.setFont("Helvetica", 8)
		canvas.setFillColor(colors.HexColor("#626963"))
		canvas.drawString(18 * mm, 10 * mm, "Open E-Sign ERPNext | Completion record")
		canvas.drawRightString(192 * mm, 10 * mm, f"Page {document.page}")
		canvas.restoreState()

	doc.build(story, onFirstPage=footer, onLaterPages=footer)
	return buffer.getvalue()


def append_certificate(pdf_bytes: bytes, certificate_bytes: bytes) -> bytes:
	"""Append the certificate PDF to the signed document."""
	base = fitz.open(stream=pdf_bytes, filetype="pdf")
	cert = fitz.open(stream=certificate_bytes, filetype="pdf")
	try:
		base.insert_pdf(cert)
		return base.tobytes(garbage=4, deflate=True)
	finally:
		base.close()
		cert.close()


def render_page_thumbnail(pdf_bytes: bytes, page_no: int = 1, zoom: float = 0.4) -> bytes:
	"""Render a PNG thumbnail of a page (used for template/library previews)."""
	with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
		page = doc[max(0, min(page_no - 1, doc.page_count - 1))]
		matrix = fitz.Matrix(zoom, zoom)
		pix = page.get_pixmap(matrix=matrix, alpha=False)
		return pix.tobytes("png")
