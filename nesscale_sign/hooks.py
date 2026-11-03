app_name = "nesscale_sign"
app_title = "E-Sign"
app_publisher = "Open E-Sign contributors"
app_description = "Electronic signatures for Frappe and ERPNext"
app_email = ""
app_license = "AGPLv3"

# Apps screen
# ------------------
add_to_apps_screen = [
	{
		"name": "nesscale_sign",
		"logo": "/assets/nesscale_sign/images/logo.svg",
		"title": "E-Sign",
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
after_migrate = "nesscale_sign.install.sync_desktop_icon"
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

# Frappe Assistant Core native custom-tools discovery; no connector fork required.
assistant_tools = [
	"nesscale_sign.mcp.fac_plugin.tools.esign_archive_template.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_builder_guide.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_combine_pdfs.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_create_contact.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_create_draft.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_create_email_account.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_create_mail_template.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_create_template.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_delete_draft.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_delete_email_account.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_download_document.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_download_file.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_duplicate_template.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_email_services.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_get_audit.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_get_contact.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_get_doctype_fields.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_get_document.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_get_email_template.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_get_readiness.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_get_settings.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_get_stats.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_get_template.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_inspect_pdf.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_list_attachments.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_list_documents.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_list_email_accounts.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_list_email_templates.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_list_mail_templates.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_list_organizations.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_list_senders.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_list_templates.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_my_pending_signatures.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_preview_email_template.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_publish_template.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_recent_activity.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_remind_document.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_render_pdf.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_resend_invitation.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_restore_email_defaults.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_retry_completion.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_revise_unsigned.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_save_document_fields.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_save_email_template.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_save_organization.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_save_template_fields.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_save_template_roles.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_search_contacts.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_search_doctypes.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_send_document.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_set_template_pdf.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_throughput.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_trigger_events.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_update_draft.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_update_email_account.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_update_settings.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_update_template.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_upload_image.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_upload_pdf.Tool",
	"nesscale_sign.mcp.fac_plugin.tools.esign_void_document.Tool",
]


assistant_tools.append("nesscale_sign.mcp.fac_plugin.tools.esign_workflow_guide.Tool")
assistant_skills = [
	{
		"app": "nesscale_sign",
		"manifest": "mcp/skills/manifest.json",
		"content_dir": "mcp/skills",
	}
]
