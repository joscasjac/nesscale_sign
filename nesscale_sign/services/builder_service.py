"""Render bounded, structured document blocks into a fixed signing PDF."""

import base64
import io
import json
import math
from html import escape

import frappe
from PIL import Image as PILImage
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle


def render_document(data):
	if isinstance(data, str):
		if len(data) > 10_000_000:
			frappe.throw("Document content is too large.")
		data = json.loads(data)
	if not isinstance(data, dict):
		frappe.throw("Invalid document content.")
	pages = data.get("pages", [])
	if not isinstance(pages, list) or not 1 <= len(pages) <= 20:
		frappe.throw("Use between 1 and 20 builder pages.")
	if len(json.dumps(data)) > 10_000_000:
		frappe.throw("Document content is too large.")
	out = io.BytesIO()
	pdf = canvas.Canvas(out, pagesize=(595, 842))
	count = 0
	for page in pages:
		if not isinstance(page, dict):
			frappe.throw("Invalid document page.")
		blocks = page.get("blocks", [])
		if not isinstance(blocks, list):
			frappe.throw("Invalid page blocks.")
		for block in blocks:
			count += 1
			if count > 200:
				frappe.throw("Use at most 200 content blocks.")
			_draw_block(pdf, block)
		pdf.showPage()
	pdf.save()
	return out.getvalue()


def _draw_block(pdf, b):
	if not isinstance(b, dict):
		frappe.throw("Invalid content block.")
	try:
		x, top, w, h = [float(b.get(k, 0)) for k in ("x", "y", "width", "height")]
		size = float(b.get("font_size", 12))
		if not all(math.isfinite(v) for v in (x, top, w, h, size)) or not (
			0 <= x < 595
			and 0 <= top < 842
			and w >= 10
			and h >= 10
			and x + w <= 595
			and top + h <= 842
			and 6 <= size <= 48
		):
			raise ValueError
		color = HexColor(b.get("color") or "#24362d")
		background = HexColor(b.get("background") or "#ffffff")
	except ValueError, TypeError:
		frappe.throw("Blocks must fit on the page with a font size between 6 and 48.")
	y = 842 - top - h
	pdf.setFillColor(background)
	pdf.rect(x, y, w, h, stroke=0, fill=1)
	kind = b.get("type")
	text = str(b.get("text") or "")
	if len(text) > 20000:
		frappe.throw("A content block is too long.")
	if kind == "Image":
		try:
			encoded = b.get("image", "")
			if len(encoded) > 3_000_000 or not encoded.startswith(
				("data:image/png;base64,", "data:image/jpeg;base64,")
			):
				raise ValueError
			image = PILImage.open(io.BytesIO(base64.b64decode(encoded.split(",", 1)[1], validate=True)))
			if image.width * image.height > 4_000_000:
				raise ValueError
			image.load()
			pdf.drawImage(ImageReader(image), x, y, w, h, preserveAspectRatio=True, anchor="c", mask="auto")
		except ValueError, OSError:
			frappe.throw("Choose a PNG or JPG image smaller than 2 MB and 4 megapixels.")
	elif kind == "Divider":
		pdf.setStrokeColor(color)
		pdf.line(x, y + h / 2, x + w, y + h / 2)
	elif kind in ("Heading", "Text", "Table", "Video link"):
		style = ParagraphStyle(
			"content",
			fontName="Helvetica-Bold" if kind == "Heading" else "Helvetica",
			fontSize=size,
			leading=size * 1.35,
			textColor=color,
		)
		if kind == "Table":
			rows = [line.split("\t") for line in text.splitlines()]
			if not rows or len(rows) > 100 or max(map(len, rows)) > 8:
				frappe.throw("Use at most 100 rows and 8 columns per table.")
			columns = max(map(len, rows))
			content = [
				[Paragraph(escape(cell), style) for cell in row] + [""] * (columns - len(row)) for row in rows
			]
			item = Table(content, colWidths=[w / columns] * columns)
			item.setStyle(
				TableStyle(
					[
						("GRID", (0, 0), (-1, -1), 0.4, color),
						("VALIGN", (0, 0), (-1, -1), "TOP"),
						("BACKGROUND", (0, 0), (-1, 0), HexColor("#edf1ec")),
					]
				)
			)
		else:
			item = Paragraph(escape(text).replace("\n", "<br/>"), style)
		_, used = item.wrap(w, h)
		if used > h:
			frappe.throw("A text or table block overflows. Increase its height or shorten its content.")
		item.drawOn(pdf, x, y + h - used)
	else:
		frappe.throw("Unsupported content block.")
