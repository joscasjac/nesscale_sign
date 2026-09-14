"""Literal document merge values. No expressions or template evaluation."""

import json
import re
from html import escape
from html.parser import HTMLParser

import frappe

TOKEN = re.compile(r"{{\s*([A-Za-z][A-Za-z0-9_.]*)\s*}}")


def variable_values(data):
	items = data.get("resolvedVariables", [])
	if not isinstance(items, list) or len(items) > 100:
		frappe.throw("Use at most 100 document variables.")
	result = {}
	for item in items:
		if not isinstance(item, dict) or not re.fullmatch(
			r"[A-Za-z][A-Za-z0-9_.]{0,100}", str(item.get("key", ""))
		):
			frappe.throw("Invalid document variable.")
		value = str(item.get("value") or "")
		if len(value) > 20000:
			frappe.throw("A document variable is too long.")
		result[item["key"]] = value
	return result


def merge_text(text, values):
	def replace(match):
		key = match[1]
		if key not in values or values[key] == "":
			frappe.throw("Set a value for document variable: " + key)
		return values[key]

	return TOKEN.sub(replace, str(text or ""))


def envelope_values(doc):
	return variable_values(json.loads(doc.get("builder_json") or "{}"))


class SafeParagraph(HTMLParser):
	"""Allowlisted formatting with merge tokens resolved across text-node boundaries."""

	def __init__(self, values):
		super().__init__(convert_charrefs=True)
		self.parts = []
		self.values = values
		self.lists = []
		self.tags = {"b": "b", "strong": "b", "i": "i", "em": "i", "u": "u", "s": "strike"}

	def markup(self, value):
		self.parts.append([False, value])

	def handle_starttag(self, tag, attrs):
		if tag in self.tags:
			self.markup("<" + self.tags[tag] + ">")
		elif tag == "br":
			self.markup("<br/>")
		elif tag in ("p", "div", "li") and self.parts:
			self.markup("<br/>")
		if tag in ("ol", "ul"):
			self.lists.append([tag, 0])
		if tag == "li":
			if self.lists and self.lists[-1][0] == "ol":
				self.lists[-1][1] += 1
				self.handle_data(str(self.lists[-1][1]) + ". ")
			else:
				self.handle_data("• ")

	def handle_endtag(self, tag):
		if tag in self.tags:
			self.markup("</" + self.tags[tag] + ">")
		if tag in ("ol", "ul") and self.lists:
			self.lists.pop()

	def handle_data(self, text):
		self.parts.append([True, text])

	def result(self):
		segments = []
		offset = 0
		for part in self.parts:
			if part[0]:
				segments.append((part, offset, offset + len(part[1])))
				offset += len(part[1])
		plain = "".join(part[1] for part, _, _ in segments)
		for match in reversed(list(TOKEN.finditer(plain))):
			value = merge_text(match[0], self.values)
			for part, start, end in segments:
				if start < match.end() and end > match.start():
					left = max(0, match.start() - start)
					right = min(end - start, match.end() - start)
					part[1] = (
						part[1][:left] + (value if start <= match.start() < end else "") + part[1][right:]
					)
		return "".join(escape(value) if text else value for text, value in self.parts)


def rich_paragraph(html, values):
	if len(html) > 100000:
		frappe.throw("A text block is too large.")
	parser = SafeParagraph(values)
	parser.feed(html)
	return parser.result()
