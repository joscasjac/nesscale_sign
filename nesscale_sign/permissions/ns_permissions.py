# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Row-level permission scoping for envelopes and templates.

Managers (``System Manager`` / ``Nesscale Sign Manager``) see everything.
Regular ``Nesscale Sign User`` accounts see documents they created or sent, plus
envelopes where they are a named signer.
"""

import frappe

MANAGER_ROLES = {"System Manager", "Nesscale Sign Manager", "Administrator"}


def _is_manager(user: str) -> bool:
	if user == "Administrator":
		return True
	return bool(set(frappe.get_roles(user)) & MANAGER_ROLES)


# --------------------------------------------------------------------- envelope
def envelope_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if _is_manager(user):
		return ""
	u = frappe.db.escape(user)
	email = frappe.db.escape(frappe.db.get_value("User", user, "email") or user)
	return (
		f"(`tabNS Envelope`.owner = {u} OR `tabNS Envelope`.sender = {u} OR "
		f"EXISTS (SELECT 1 FROM `tabNS Envelope Signer` s "
		f"WHERE s.parent = `tabNS Envelope`.name AND s.signer_email = {email}))"
	)


def envelope_has_permission(doc, user: str | None = None, permission_type=None) -> bool:
	user = user or frappe.session.user
	if _is_manager(user):
		return True
	if doc.owner == user or doc.sender == user:
		return True
	email = frappe.db.get_value("User", user, "email") or user
	if any((s.signer_email or "").lower() == (email or "").lower() for s in doc.signers):
		# Signers may read but not mutate the envelope through Desk.
		return permission_type in (None, "read")
	return False


# --------------------------------------------------------------------- template
def template_query_conditions(user: str | None = None) -> str:
	user = user or frappe.session.user
	if _is_manager(user):
		return ""
	u = frappe.db.escape(user)
	return f"(`tabNS Template`.owner = {u})"


def template_has_permission(doc, user: str | None = None, permission_type=None) -> bool:
	user = user or frappe.session.user
	if _is_manager(user):
		return True
	return doc.owner == user
