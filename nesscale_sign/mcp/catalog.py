"""Explicit MCP allowlist. No caller-controlled Python method execution."""


def obj(properties=None, required=()):
	return {
		"type": "object",
		"properties": properties or {},
		"required": list(required),
		"additionalProperties": False,
	}


def strings(names):
	return {name: {"type": "string"} for name in names.split()}


def integer(low, high):
	return {"type": "integer", "minimum": low, "maximum": high}


def array(items, maximum=500):
	return {"type": "array", "items": items, "maxItems": maximum}


STRING = {"type": "string", "minLength": 1}
NAME = {"name": STRING}
FLAG = {"type": ["boolean", "integer"], "enum": [True, False, 0, 1]}
ROUTING = {"enum": ["Sequential", "Parallel"]}
SIGNER = obj(
	{
		**strings("role_key role_label signer_name signer_email color"),
		"signing_order": integer(1, 100),
		"auth_method": {"enum": ["None", "Email"]},
	},
	["signer_name", "signer_email"],
)
DATA = obj(
	{
		**strings(
			"title organization email_template email_subject email_message message email_from_name email_from_account expires_on source_doctype source_name completion_redirect_url"
		),
		"routing_type": ROUTING,
		"email_mode": {"enum": ["template", "custom"]},
		"completion_redirect_target": {"enum": ["Same tab", "New tab"]},
		"email_attachments": {"type": "string", "description": "JSON array of readable File record names."},
		"signers": array(SIGNER, 100),
	}
)
FIELD = obj(
	{
		**strings(
			"field_key label signer_role placeholder options font_family validation repeat_group mapping_key"
		),
		"field_type": {
			"enum": [
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
			]
		},
		"page": integer(1, 100),
		**{
			key: {"type": "number", "minimum": 0, "maximum": 1}
			for key in ("pos_x", "pos_y", "width", "height")
		},
		"required": FLAG,
		"read_only": FLAG,
		"default_value": {"type": ["string", "number", "boolean", "null"]},
		"font_size": integer(1, 200),
		"max_length": integer(0, 10000),
	},
	["field_type", "page", "pos_x", "pos_y", "width", "height"],
)
FIELDS = array(FIELD)
ROLE = obj(
	{
		**strings("role_key role_label color source_email_field source_name_field manual_email manual_name"),
		"signing_order": integer(1, 100),
		"optional": FLAG,
	},
	["role_key", "role_label"],
)
ROLES = array(ROLE, 100)
TEMPLATE_DATA = obj(
	{
		**strings(
			"title description organization email_subject email_message builder_json tags trigger_doctype trigger_value_field trigger_value_to trigger_date_field"
		),
		"routing_type": ROUTING,
		"expiry_days": integer(1, 3650),
		"reminder_enabled": FLAG,
		"auto_create": FLAG,
		"trigger_auto_send": FLAG,
		"trigger_event": {
			"enum": ["New", "Save", "Submit", "Cancel", "Value Change", "Days Before", "Days After"]
		},
		"trigger_days": integer(0, 3650),
	}
)
TEMPLATE_CREATE = obj(
	{
		**{k: v for k, v in TEMPLATE_DATA["properties"].items() if k not in ("tags", "reminder_enabled")},
		"pdf_file": STRING,
		"signer_roles": ROLES,
	}
)
PAGING = {**strings("search status"), "start": integer(0, 1000000), "page_length": integer(1, 100)}
CONTENT = {
	"type": "object",
	"description": "Document builder JSON; call esign_builder_guide for format and example.",
}
SETTINGS = obj(
	{
		**strings("default_organization support_email public_base_url sender_email email_footer"),
		"enforce_audit_chain": FLAG,
	}
)
ORGANIZATION = obj(
	{
		**strings(
			"name organization_name description brand_color default_sender_name default_sender_email timezone"
		),
		"disabled": FLAG,
		"default_expiry_days": integer(1, 3650),
		"reminder_enabled": FLAG,
		"reminder_interval_days": integer(1, 365),
		"reminder_max_count": integer(0, 100),
		"require_all_fields": FLAG,
	}
)
EMAIL = obj({**strings("name subject response response_html"), "use_html": FLAG}, ["name", "subject"])
ACCOUNT = obj(
	{
		**strings(
			"email_account_name email_id service smtp_server email_server password api_key api_secret frappe_mail_site"
		),
		**{
			key: FLAG
			for key in "enable_incoming enable_outgoing default_incoming default_outgoing use_imap use_ssl".split()
		},
		"smtp_port": integer(1, 65535),
	}
)
ACCOUNT_UPDATE = obj(
	{
		**strings("email_account_name password"),
		**{key: FLAG for key in "enable_incoming enable_outgoing default_incoming default_outgoing".split()},
	}
)
DOWNLOAD = {
	"offset": integer(0, 100000000),
	"length": integer(1, 262144),
	"include_content": {
		"type": "boolean",
		"description": "Return base64 bytes, default false (metadata only). Decode each chunk separately.",
	},
}

# name -> (module.method, description, input schema, read only)
EXTENSIONS = {}


def add(name, target, description, schema=None, read=False):
	EXTENSIONS["esign_" + name] = (target, description, schema or obj(), read)


add(
	"upload_pdf",
	"mcp.files.upload_pdf",
	"Upload a private PDF from base64 bytes (max 15 MiB, 100 pages). No remote URLs. Does not send. Use returned file_url in create_draft or template tools.",
	obj(
		{"file_name": STRING, "content_base64": {"type": "string", "minLength": 1, "maxLength": 20971520}},
		["file_name", "content_base64"],
	),
)
add(
	"upload_image",
	"mcp.files.upload_image",
	"Upload a private PNG/JPEG image for builder content or email attachments. Max 5 MiB and 16 million pixels. Does not sign a document.",
	obj(
		{"file_name": STRING, "content_base64": {"type": "string", "minLength": 1, "maxLength": 6990508}},
		["file_name", "content_base64"],
	),
)
add(
	"inspect_pdf",
	"mcp.files.inspect_pdf",
	"Read an authorized PDF's size, SHA256 and page dimensions before placing fields.",
	obj({"file_url": STRING}, ["file_url"]),
	True,
)
add(
	"download_file",
	"mcp.files.download_file",
	"Read a permitted File's metadata or bounded base64 chunk. Private URLs require login. Use download_document for document artifacts.",
	obj({"file_url": STRING, **DOWNLOAD}, ["file_url"]),
	True,
)
add(
	"download_document",
	"mcp.files.download_document",
	"Download source, signed PDF or completion certificate as metadata or base64 chunks. Signed PDF downloads are recorded in the audit trail.",
	obj(
		{**NAME, "artifact": {"enum": ["source", "signed", "certificate"]}, **DOWNLOAD}, ["name", "artifact"]
	),
)
add(
	"render_pdf",
	"api.builder.render",
	"Render builder JSON to a private PDF without creating an envelope; imported PDFs may be supplied as source_pdf.",
	obj({"data": CONTENT, "source_pdf": STRING}, ["data"]),
)
add(
	"combine_pdfs",
	"api.builder.combine_pdfs",
	"Combine readable PDFs in the supplied order; max 10 files, 15 MiB total, 100 pages. Creates a private PDF.",
	obj({"urls": {**array(STRING, 10), "minItems": 1}}, ["urls"]),
)
add(
	"create_template",
	"api.template.create_template",
	"Create a reusable template, optionally with an uploaded/rendered PDF and signer roles. Save fields then publish separately. Explicit authorization is needed to enable automatic sending.",
	obj({"data": TEMPLATE_CREATE}, ["data"]),
)
add(
	"update_template",
	"api.template.update_template",
	"Update template options and record-trigger automation. Enabling trigger_auto_send authorizes future emails; only do so on explicit user instruction.",
	obj({**NAME, "data": TEMPLATE_DATA}, ["name", "data"]),
)
add(
	"set_template_pdf",
	"api.template.set_template_pdf",
	"Replace a template's source PDF with an authorized uploaded/rendered PDF. Review field positions and publish a new version.",
	obj({**NAME, "file_url": STRING}, ["name", "file_url"]),
)
add(
	"save_template_fields",
	"api.template.save_template_fields",
	"Replace all template fields, including placement and record field mappings.",
	obj({**NAME, "fields": FIELDS}, ["name", "fields"]),
)
add(
	"save_template_roles",
	"api.template.save_template_roles",
	"Replace all template signer roles, order and contact/record mappings.",
	obj({**NAME, "roles": ROLES}, ["name", "roles"]),
)
for action, desc in [
	(
		"publish",
		"Publish a template and create a version snapshot. Active automatic sending may send future invitations.",
	),
	("archive", "Archive a template to stop its use for new documents."),
]:
	add(action + "_template", "api.template." + action + "_template", desc, obj(NAME, ["name"]))
add(
	"duplicate_template",
	"api.template.duplicate_template",
	"Copy a readable template into a new draft with its fields and roles; does not send.",
	obj({**NAME, "title": STRING}, ["name"]),
)
add(
	"save_document_fields",
	"mcp.actions.save_document_fields",
	"Replace all fields on a Draft document. Never modifies signed documents.",
	obj({**NAME, "fields": FIELDS}, ["name", "fields"]),
)
add(
	"void_document",
	"api.envelope.void_envelope",
	"Void a document using the normal lifecycle. May notify recipients; only on explicit user instruction.",
	obj({**NAME, "reason": STRING}, ["name", "reason"]),
)
add(
	"delete_draft",
	"mcp.actions.delete_draft",
	"Permanently delete a Draft document only when the user requests deletion.",
	obj(NAME, ["name"]),
)
add(
	"resend_invitation",
	"api.envelope.resend_envelope",
	"Resend an invitation to one eligible recipient. Queues email each call; do not blindly retry. Requires user instruction to send.",
	obj({**NAME, "signer_email": STRING}, ["name", "signer_email"]),
)
add(
	"remind_document",
	"api.envelope.remind_envelope",
	"Email outstanding signers a reminder. Requires explicit user instruction; repeated calls can send repeated emails.",
	obj(NAME, ["name"]),
)
add(
	"retry_completion",
	"mcp.actions.retry_completion",
	"Retry failed PDF finalization after every signer has signed. May queue completion emails. Does not add signatures.",
	obj(NAME, ["name"]),
)
add(
	"get_audit",
	"api.envelope.get_audit",
	"Read document audit events and verify their hash-chain integrity.",
	obj(NAME, ["name"]),
	True,
)
add(
	"my_pending_signatures",
	"mcp.actions.my_pending_signatures",
	"List documents awaiting the authenticated user. Returns an app handoff URL; signing and consent happen in the human signing page, never as another signer.",
	read=True,
)
for name, target, desc in [
	("get_stats", "dashboard.get_stats", "Read permission-filtered signing dashboard totals."),
	("get_settings", "settings.get_settings", "Read e-sign settings (manager only)."),
	(
		"get_readiness",
		"settings.get_readiness",
		"Check outgoing email and PDF seal configuration; no credentials returned.",
	),
	("list_organizations", "settings.list_organizations", "List readable signing organizations."),
	(
		"list_email_accounts",
		"email_account.list_email_accounts",
		"List sender accounts without passwords (manager only).",
	),
	("email_services", "email_account.email_services", "List supported outgoing email providers."),
	(
		"list_email_templates",
		"email_template.list_email_templates",
		"List email templates for administration (manager only).",
	),
	("list_mail_templates", "mail.list_templates", "List readable email templates for document invitations."),
	("list_senders", "mail.list_senders", "List outgoing accounts available to the user."),
	("trigger_events", "integration.trigger_events", "List supported document automation triggers."),
]:
	add(name, "api." + target, desc, read=True)
add(
	"recent_activity",
	"api.dashboard.recent_activity",
	"Read recent accessible signing documents.",
	obj({"limit": integer(1, 100)}),
	True,
)
add(
	"throughput",
	"api.dashboard.throughput",
	"Read daily completion counts for accessible documents.",
	obj({"days": integer(1, 366)}),
	True,
)
add(
	"search_contacts",
	"api.contacts.search_contacts",
	"Search readable ERPNext contacts for real recipient details.",
	obj(strings("query")),
	True,
)
add(
	"get_contact",
	"api.contacts.get_contact_prefill",
	"Read contact name and primary email for document preparation.",
	obj(NAME, ["name"]),
	True,
)
add(
	"create_contact",
	"api.contacts.create_contact",
	"Create a contact with supplied name and email; never sends.",
	obj({"full_name": STRING, "email_id": STRING}, ["full_name", "email_id"]),
)
add(
	"update_settings",
	"api.settings.update_settings",
	"Update e-sign settings (manager only). Changes affect future signing workflows.",
	obj({"data": SETTINGS}, ["data"]),
)
add(
	"save_organization",
	"api.settings.save_organization",
	"Create or update signing organization settings (manager only).",
	obj({"data": ORGANIZATION}, ["data"]),
)
add(
	"create_email_account",
	"api.email_account.create_email_account",
	"Configure an outgoing/incoming email account (manager only). May connect to the specified provider. Pass credentials through a trusted client; never echo them.",
	obj({"data": ACCOUNT}, ["data"]),
)
add(
	"update_email_account",
	"api.email_account.update_email_account",
	"Update account flags, name or password (manager only). Never echo credentials.",
	obj({**NAME, "data": ACCOUNT_UPDATE}, ["name", "data"]),
)
add(
	"delete_email_account",
	"api.email_account.delete_email_account",
	"Delete a sender account (manager only), affecting email delivery. Requires explicit user instruction.",
	obj(NAME, ["name"]),
)
add(
	"get_email_template",
	"api.email_template.get_email_template",
	"Read an editable email template (manager only).",
	obj(NAME, ["name"]),
	True,
)
add(
	"save_email_template",
	"api.email_template.save_email_template",
	"Create or replace an email template body and subject (manager only).",
	obj({"data": EMAIL}, ["data"]),
)
add(
	"preview_email_template",
	"api.email_template.preview",
	"Render an email subject/body against sample signing data; does not send (manager only).",
	obj({"data": obj(strings("subject response"))}, ["data"]),
	True,
)
add(
	"restore_email_defaults",
	"api.email_template.restore_defaults",
	"Overwrite the shipped email templates with defaults (manager only). Requires explicit request; discards template customizations.",
)
add(
	"create_mail_template",
	"api.mail.create_template",
	"Create a plain-text invitation template with normal Email Template permissions.",
	obj({"name": STRING, "subject": STRING, "body": STRING}, ["name", "subject", "body"]),
)
add(
	"list_attachments",
	"mcp.actions.list_attachments",
	"Validate readable attachment File records and return their names.",
	obj({"names": array(STRING, 20)}, ["names"]),
	True,
)
add(
	"search_doctypes",
	"api.integration.search_doctypes",
	"Discover normal DocTypes for template automation (manager only).",
	obj(strings("txt")),
	True,
)
add(
	"get_doctype_fields",
	"api.integration.get_doctype_fields",
	"Discover mappable fields for template automation (manager only).",
	obj({"doctype": STRING}, ["doctype"]),
	True,
)

MANAGER_TOOLS = {
	"esign_get_settings",
	"esign_get_readiness",
	"esign_search_doctypes",
	"esign_get_doctype_fields",
}
EXTERNAL_TOOLS = {
	"esign_send_document",
	"esign_resend_invitation",
	"esign_remind_document",
	"esign_void_document",
	"esign_retry_completion",
	"esign_create_email_account",
	"esign_update_email_account",
	"esign_create_template",
	"esign_update_template",
	"esign_publish_template",
}
DESTRUCTIVE_TOOLS = {
	"esign_update_draft",
	"esign_revise_unsigned",
	"esign_update_template",
	"esign_set_template_pdf",
	"esign_save_template_fields",
	"esign_save_template_roles",
	"esign_save_document_fields",
	"esign_void_document",
	"esign_delete_draft",
	"esign_update_settings",
	"esign_save_organization",
	"esign_update_email_account",
	"esign_delete_email_account",
	"esign_save_email_template",
	"esign_restore_email_defaults",
	"esign_archive_template",
}

add(
	"workflow_guide",
	"mcp.actions.workflow_guide",
	"Start here for ERPNext signable documents, contracts, NDAs, contractor agreements, PDF uploads and sending for electronic signature. Explains the Nesscale Sign/Open E-Sign MCP workflow and available actions; returns instructions only, never creates or sends.",
	read=True,
)
