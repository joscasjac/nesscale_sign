# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""App-screen permission gate."""

import frappe


def has_app_permission():
	"""Whether the current user may see Nesscale Sign on the apps screen."""
	if frappe.session.user == "Administrator":
		return True
	allowed = {"System Manager", "Nesscale Sign Manager", "Nesscale Sign User"}
	return bool(set(frappe.get_roles()) & allowed)
