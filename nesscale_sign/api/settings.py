# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Settings & organization API endpoints."""

import frappe

from nesscale_sign.api import load, require_manager

# NOTE: brand/white-label fields (e.g. signing_brand_name) are intentionally
# excluded for now — branding is fixed to "Open E-Sign". They will return with
# the white-label plan so customers can set their own brand/logo.
SETTINGS_FIELDS = (
	"default_organization",
	"support_email",
	"public_base_url",
	"enforce_audit_chain",
	"sender_email",
	"email_footer",
)


@frappe.whitelist()
def get_settings():
	doc = frappe.get_single("NS Settings")
	return {field: doc.get(field) for field in SETTINGS_FIELDS}


@frappe.whitelist()
def update_settings(data: dict | None = None):
	require_manager()
	doc = frappe.get_single("NS Settings")
	data = load(data) or {}
	for field in SETTINGS_FIELDS:
		if field in data:
			doc.set(field, data[field])
	doc.save()
	return get_settings()


@frappe.whitelist()
def list_organizations():
	return frappe.get_list(
		"NS Organization",
		fields=[
			"name",
			"organization_name",
			"brand_color",
			"disabled",
			"default_expiry_days",
			"reminder_enabled",
			"reminder_interval_days",
			"reminder_max_count",
		],
		order_by="organization_name asc",
		limit_page_length=0,
	)


@frappe.whitelist()
def save_organization(data: dict | None = None):
	require_manager()
	data = load(data) or {}
	name = data.get("name")
	if name and frappe.db.exists("NS Organization", name):
		doc = frappe.get_doc("NS Organization", name)
	else:
		doc = frappe.new_doc("NS Organization")
	for field in (
		"organization_name",
		"description",
		"brand_color",
		"disabled",
		"default_sender_name",
		"default_sender_email",
		"timezone",
		"default_expiry_days",
		"reminder_enabled",
		"reminder_interval_days",
		"reminder_max_count",
		"require_all_fields",
	):
		if field in data:
			doc.set(field, data[field])
	doc.save()
	return doc.as_dict()


@frappe.whitelist()
def get_readiness():
	return {
		"email_configured": bool(frappe.db.exists("Email Account", {"enable_outgoing": 1})),
		"seal_configured": bool(frappe.conf.get("esign_pkcs12_path")),
		"seal_required": bool(frappe.conf.get("esign_require_seal")),
	}
