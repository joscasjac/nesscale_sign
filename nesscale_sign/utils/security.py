"""Shared server-side boundaries for signing and document access."""

import hashlib
import math
from datetime import date

import frappe

CONSENT_VERSION = "2026-09-11"
CONSENT_TEXT = "I have reviewed this document and agree to sign it electronically."


def lock_envelope(name):
	# Serialize state changes AND audit-chain appends on the same parent row.
	frappe.db.sql("SELECT name FROM `tabNS Envelope` WHERE name=%s FOR UPDATE", (name,))


def digest(content):
	return hashlib.sha256(content).hexdigest()


def public_envelope(doc):
	data = doc.as_dict()
	for signer in data.get("signers", []):
		for key in ("token", "signing_session"):
			signer.pop(key, None)
	return data


def validate_fields(fields, page_count):
	if not isinstance(fields, list) or len(fields) > 500:
		frappe.throw("Use at most 500 fields per document.")
	keys = set()
	allowed = {
		"Signature",
		"Initial",
		"Name",
		"Email",
		"Date Signed",
		"Date",
		"Text",
		"Checkbox",
		"Dropdown",
		"Label",
		"Stamp",
	}
	for field in fields:
		if field.get("field_type") not in allowed:
			frappe.throw("Unsupported field type.")
		try:
			page = int(field.get("page", 1))
			x, y, w, h = [float(field.get(k, 0)) for k in ("pos_x", "pos_y", "width", "height")]
		except TypeError, ValueError:
			frappe.throw("Invalid field coordinates.")
		if not all(math.isfinite(n) for n in (x, y, w, h)) or not (
			1 <= page <= page_count
			and x >= 0
			and y >= 0
			and w > 0
			and h > 0
			and x + w <= 1.001
			and y + h <= 1.001
		):
			frappe.throw("Fields must fit within a document page.")
		key = field.get("field_key")
		if key and key in keys:
			frappe.throw("Field identifiers must be unique.")
		keys.add(key)


def validate_value(row, value):
	if isinstance(value, (list, dict)) or len(str(value or "")) > 10000:
		frappe.throw("Field value is too long or invalid.")
	if row.get("field_type") == "Date" and value not in (None, ""):
		try:
			if not isinstance(value, str) or date.fromisoformat(value).isoformat() != value:
				raise ValueError
		except ValueError, TypeError:
			frappe.throw("Choose a valid date in YYYY-MM-DD format.")
	if row.get("field_type") == "Dropdown":
		options = (row.get("options") or "").splitlines()
		if value not in (None, "") and value not in options:
			frappe.throw("Choose one of the available options.")
	return value
