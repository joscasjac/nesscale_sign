# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Thin API layer for Nesscale Sign.

Endpoint functions validate input, delegate to the service layer, and shape the
response. No business logic lives here.
"""

import json

import frappe


def load(value):
	"""Coerce a possibly JSON-encoded argument into a Python object."""
	if value is None:
		return None
	if isinstance(value, str):
		try:
			return json.loads(value)
		except (ValueError, TypeError):
			return value
	return value


def require_manager():
	if not is_manager():
		frappe.throw(frappe._("Not permitted"), frappe.PermissionError)


def is_manager() -> bool:
	roles = set(frappe.get_roles())
	return bool(roles & {"System Manager", "Nesscale Sign Manager"})
