"""Render bounded, structured document blocks into a fixed signing PDF."""

import base64
import io
import json
import math
from html import escape

import frappe
from PIL import Image as PILImage
from PIL import ImageOps
from reportlab.lib.colors import HexColor
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.platypus import Paragraph, Table, TableStyle

from nesscale_sign.services.document_variables import merge_text, rich_paragraph, variable_values


def render_document(data, max_pages=20, page_sizes=None):
	if isinstance(data, str):
		if len(data) > 10_000_000:
			frappe.throw("Document content is too large.")
		data = json.loads(data)
	if not isinstance(data, dict):
		frappe.throw("Invalid document content.")
	pages = data.get("pages", [])
	if not isinstance(pages, list) or not 1 <= len(pages) <= max_pages:
		frappe.throw(f"Use between 1 and {max_pages} builder pages.")
	if len(json.dumps(data)) > 10_000_000:
		frappe.throw("Document content is too large.")
	values = variable_values(data)
	out = io.BytesIO()
	pdf = canvas.Canvas(out, pagesize=(595, 842))
	count = 0
	for page_index, page in enumerate(pages):
		page_width, page_height = page_sizes[page_index] if page_sizes else (595,842)
		pdf.setPageSize((page_width,page_height))
		if not isinstance(page, dict):
			frappe.throw("Invalid document page.")
		blocks = page.get("blocks", [])
		if not isinstance(blocks, list):
			frappe.throw("Invalid page blocks.")
		for block in blocks:
			count += 1
			if count > 200:
				frappe.throw("Use at most 200 content blocks.")
			_draw_block(pdf, block, values, page_width, page_height)
		pdf.showPage()
	pdf.save()
	return out.getvalue()


def _draw_block(pdf, b, values=None, page_width=595, page_height=842):
	values = values or {}
	if isinstance(b, dict) and b.get("type") == "Field":
		return
	if not isinstance(b, dict):
		frappe.throw("Invalid content block.")
	try:
		x, top, w, h = [float(b.get(k, 0)) for k in ("x", "y", "width", "height")]
		size = float(b.get("font_size", 12))
		if not all(math.isfinite(v) for v in (x, top, w, h, size)) or not (
			0 <= x < page_width
			and 0 <= top < page_height
			and w >= 10
			and h >= 10
			and x + w <= page_width
			and top + h <= page_height
			and 6 <= size <= 48
		):
			raise ValueError
		color = HexColor(b.get("color") or "#24362d")
		background = HexColor(b.get("background") or "#ffffff")
	except ValueError, TypeError:
		frappe.throw("Blocks must fit on the page with a font size between 6 and 48.")
	y = page_height - top - h
	pdf.setFillColor(background)
	pdf.rect(x, y, w, h, stroke=0, fill=1)
	kind = b.get("type")
	text = merge_text(b.get("text"), values)
	try:
		padding = float(b.get("padding", 0))
		if not math.isfinite(padding) or not 0 <= padding <= 80 or 2 * padding >= min(w, h):
			raise ValueError
	except ValueError, TypeError:
		frappe.throw("Invalid block padding.")
	x, y, w, h = x + padding, y + padding, w - 2 * padding, h - 2 * padding
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
			if b.get("grayscale"):
				image = ImageOps.grayscale(image).convert("RGB")
			iw = min(w, float(b.get("image_width") or w))
			ih = min(h, float(b.get("image_height") or h))
			offset = (w - iw) * {"left": 0, "center": 0.5, "right": 1}.get(b.get("align"), 0)
			pdf.drawImage(
				ImageReader(image),
				x + offset,
				y + h - ih,
				iw,
				ih,
				preserveAspectRatio=True,
				anchor="c",
				mask="auto",
			)
		except ValueError, OSError:
			frappe.throw("Choose a PNG or JPG image smaller than 2 MB and 4 megapixels.")
	elif kind == "Divider":
		pdf.setStrokeColor(color)
		pdf.line(x, y + h / 2, x + w, y + h / 2)
	elif kind in ("Heading", "Text", "Table"):
		font = {"Arial": "Helvetica", "Times New Roman": "Times-Roman", "Courier New": "Courier"}.get(
			b.get("font_family"), "Helvetica"
		)
		if kind == "Heading":
			font = {"Helvetica": "Helvetica-Bold", "Times-Roman": "Times-Bold", "Courier": "Courier-Bold"}[
				font
			]
		style = ParagraphStyle(
			"content",
			fontName=font,
			fontSize=size,
			leading=size * max(1, min(2, float(b.get("line_height", 1.35)))),
			alignment={"left": 0, "center": 1, "right": 2}.get(b.get("align"), 0),
			textColor=color,
		)
		if kind == "Table":
			rows = b.get("cells") or [line.split("\t") for line in text.splitlines()]
			if not isinstance(rows, list) or any(
				not isinstance(row, list) or any(not isinstance(cell, str) for cell in row) for row in rows
			):
				frappe.throw("Invalid table cells.")
			rows = [[merge_text(cell, values) for cell in row] for row in rows]
			if not rows or len(rows) > 100 or max(map(len, rows)) > 8:
				frappe.throw("Use at most 100 rows and 8 columns per table.")
			columns = max(map(len, rows))
			content = [
				[Paragraph(escape(cell).replace("\n", "<br/>"), style) for cell in row]
				+ [""] * (columns - len(row))
				for row in rows
			]
			item = Table(content, colWidths=[w / columns] * columns)
			item.setStyle(
				TableStyle(
					[
						("GRID", (0, 0), (-1, -1), 0.4, color),
						("VALIGN", (0, 0), (-1, -1), "TOP"),
						("TOPPADDING", (0, 0), (-1, -1), 8),
						("BOTTOMPADDING", (0, 0), (-1, -1), 8),
						("LEFTPADDING", (0, 0), (-1, -1), 8),
						("RIGHTPADDING", (0, 0), (-1, -1), 8),
						("BACKGROUND", (0, 0), (-1, 0), HexColor("#edf1ec")),
					]
				)
			)
		else:
			if b.get("html"):
				from bs4 import BeautifulSoup, Tag

				soup = BeautifulSoup(str(b["html"]), "html.parser")
				# Normalize tokens across formatting before splitting into paragraphs.
				markup = rich_paragraph(str(soup), values)
				sections = list(soup.children)
				if any(
					isinstance(section, Tag) and section.name in ("h1", "h2", "h3", "h4", "h5", "p", "div")
					for section in sections
				):
					used = 0
					for n, section in enumerate(sections):
						if not str(section).strip():
							continue
						level = section.name if isinstance(section, Tag) else "p"
						sz = {"h1": 32, "h2": 28, "h3": 24, "h4": 20, "h5": 18}.get(level, size)
						part_style = ParagraphStyle(
							"section",
							parent=style,
							fontSize=sz,
							leading=sz * (1.2 if level.startswith("h") else float(b.get("line_height", 1.5))),
							fontName=(
								{
									"Helvetica": "Helvetica-Bold",
									"Times-Roman": "Times-Bold",
									"Courier": "Courier-Bold",
								}.get(font, font)
								if level.startswith("h")
								else font
							),
						)
						part = Paragraph(rich_paragraph(str(section), values), part_style)
						_, height = part.wrap(w, h)
						used += height
						if used > h + 0.5:
							frappe.throw("Text exceeds its page space. Shorten it or add a page.")
						part.drawOn(pdf, x, y + h - used)
						if n < len(sections) - 1:
							used += 16
					return
			else:
				markup = escape(text).replace("\n", "<br/>")
			item = Paragraph(markup, style)
		_, used = item.wrap(w, h)
		if used > h:
			frappe.throw("A text or table block overflows. Increase its height or shorten its content.")
		item.drawOn(pdf, x, y + h - used)
	else:
		frappe.throw("Unsupported content block.")
