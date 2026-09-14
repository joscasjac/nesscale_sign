# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import frappe

ROLES = [
	{"role_name": "Nesscale Sign Manager", "desk_access": 1},
	{"role_name": "Nesscale Sign User", "desk_access": 1},
]


def before_install():
	pass


def after_install():
	create_roles()
	create_default_organization()
	ensure_settings()
	seed_emails()
	frappe.db.commit()  # nosemgrep: frappe-manual-commit — install hook, must persist seed data


def seed_emails():
	from nesscale_sign.email.seed import seed_email_templates

	seed_email_templates()


def create_roles():
	for role in ROLES:
		if not frappe.db.exists("Role", role["role_name"]):
			frappe.get_doc(
				{
					"doctype": "Role",
					"role_name": role["role_name"],
					"desk_access": role["desk_access"],
				}
			).insert(ignore_permissions=True)


def create_default_organization():
	if not frappe.db.exists("NS Organization", "Default Organization"):
		frappe.get_doc(
			{
				"doctype": "NS Organization",
				"organization_name": "Default Organization",
				"brand_color": "#2563EB",
				"default_expiry_days": 30,
				"reminder_enabled": 1,
				"reminder_interval_days": 3,
				"reminder_max_count": 3,
			}
		).insert(ignore_permissions=True)


def ensure_settings():
	settings = frappe.get_single("NS Settings")
	if not settings.default_organization and frappe.db.exists("NS Organization", "Default Organization"):
		settings.default_organization = "Default Organization"
	if not settings.signing_brand_name:
		settings.signing_brand_name = "Open E-Sign"
	settings.flags.ignore_permissions = True
	settings.save(ignore_permissions=True)


def before_tests():
	"""Create baseline fixtures for the test runner."""
	create_roles()
	create_default_organization()
	ensure_settings()
	seed_emails()
	frappe.db.commit()  # nosemgrep: frappe-manual-commit — test fixture setup
