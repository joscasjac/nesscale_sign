app_name = "nesscale_sign"
app_title = "Open E-Sign ERPNext"
app_publisher = "Nesscale Solutions Pvt Ltd"
app_description = "Electronic signatures for Frappe and ERPNext"
app_email = "info@nesscale.com"
app_license = "AGPLv3"

# Apps screen
# ------------------
add_to_apps_screen = [
	{
		"name": "nesscale_sign",
		"logo": "/assets/nesscale_sign/images/logo.svg",
		"title": "Open E-Sign ERPNext",
		"route": "/nesscale-sign",
		"has_permission": "nesscale_sign.api.permission.has_app_permission",
	}
]

# Website / SPA routing
# ------------------
website_route_rules = [
	{"from_route": "/nesscale-sign", "to_route": "nesscale_sign"},
	{"from_route": "/nesscale-sign/<path:app_path>", "to_route": "nesscale_sign"},
	{"from_route": "/sign", "to_route": "nesscale_sign"},
	{"from_route": "/sign/<path:app_path>", "to_route": "nesscale_sign"},
]

# Installation
# ------------------
after_install = "nesscale_sign.install.after_install"
before_tests = "nesscale_sign.install.before_tests"

# Permissions
# -----------
permission_query_conditions = {
	"NS Envelope": "nesscale_sign.permissions.ns_permissions.envelope_query_conditions",
	"NS Template": "nesscale_sign.permissions.ns_permissions.template_query_conditions",
}

has_permission = {
	"NS Envelope": "nesscale_sign.permissions.ns_permissions.envelope_has_permission",
	"NS Template": "nesscale_sign.permissions.ns_permissions.template_has_permission",
}

# Document Events
# ---------------
# Universal dispatcher: auto-create envelopes on configured reference-document
# events, and void them when the reference document is cancelled or deleted.
doc_events = {
	"*": {
		"after_insert": "nesscale_sign.services.integration_service.on_doc_event",
		"on_update": "nesscale_sign.services.integration_service.on_doc_event",
		"on_submit": "nesscale_sign.services.integration_service.on_doc_event",
		"on_cancel": "nesscale_sign.services.integration_service.on_doc_event",
		"on_trash": "nesscale_sign.services.integration_service.on_doc_event",
	}
}

# Scheduled Tasks
# ---------------
scheduler_events = {
	"daily": [
		"nesscale_sign.jobs.reminders.send_reminders",
		"nesscale_sign.jobs.expiration.expire_envelopes",
		"nesscale_sign.jobs.triggers.trigger_date_based",
	],
	"hourly": [
		"nesscale_sign.jobs.expiration.expire_sessions",
	],
}

# Fixtures
# --------
fixtures = [
	{"dt": "Role", "filters": [["name", "in", ["Nesscale Sign Manager", "Nesscale Sign User"]]]},
]

# Evidence and field access inherits its parent envelope/template permissions.
for _dt in ("NS Envelope Field", "NS Signature", "NS Audit Log", "NS Signing Session", "NS Notification"):
	has_permission[_dt] = "nesscale_sign.permissions.ns_permissions.related_has_permission"
for _dt in ("NS Template Field", "NS Template Version"):
	has_permission[_dt] = "nesscale_sign.permissions.ns_permissions.template_child_has_permission"

# Optional Frappe Assistant Core plugin discovery (requires fac_plugins hook support).
fac_plugins = ["nesscale_sign.mcp.fac_plugin"]
