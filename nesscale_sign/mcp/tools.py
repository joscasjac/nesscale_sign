"""Permission-checked assistant actions using the same services as the editor."""

import copy
import json
from urllib.parse import quote

import frappe
from jsonschema import ValidationError, validate

from nesscale_sign.api import builder, envelope, template
from nesscale_sign.utils.security import lock_envelope


def obj(properties, required=()):
	return {
		"type": "object",
		"properties": properties,
		"required": list(required),
		"additionalProperties": False,
	}


STRING = {"type": "string", "minLength": 1}
NAME = {"name": STRING}
DATA = {
	"type": "object",
	"description": "Envelope options: title, signers (role_key, signer_name, signer_email), routing_type, email_mode, email_template, email_subject, email_message, email_from_name, email_from_account, email_attachments, expires_on, source_doctype and source_name. Never set status or signing tokens.",
}
CONTENT = {
	"type": "object",
	"description": "Builder JSON: pages[].blocks[] with id, type (Text/Heading/Image/Table/Divider/Field), x,y,width,height in PDF points on 595x842 A4 pages; text or sanitized html, font_size, padding. Field blocks refer to field_key. resolvedVariables is an array of {key,value}. Call esign_builder_guide first.",
}
FIELDS = {
	"type": "array",
	"maxItems": 500,
	"items": {"type": "object"},
	"description": "Signing fields with field_key, field_type, signer_role matching a recipient role_key, page (1-based), pos_x,pos_y,width,height (fractions 0..1), required, default_value and mapping_key. Replaces all fields when updating.",
}

TOOLS = {
	"esign_builder_guide": (
		"Read the document builder format and workflow before creating a document. No changes.",
		obj({}),
		True,
	),
	"esign_list_templates": (
		"List readable e-sign templates. Use esign_get_template to inspect roles and fields before using one.",
		obj({"search": {"type": "string"}}),
		True,
	),
	"esign_get_template": (
		"Read an e-sign template, its recipient roles, fields and PDF dimensions.",
		obj(NAME, ["name"]),
		True,
	),
	"esign_list_documents": (
		"List accessible signing documents and statuses.",
		obj(
			{
				"search": {"type": "string"},
				"status": {"type": "string"},
				"start": {"type": "integer", "minimum": 0},
				"page_length": {"type": "integer", "minimum": 1, "maximum": 100},
			}
		),
		True,
	),
	"esign_get_document": (
		"Read a signing document, fields, audit and editor URL. Does not expose signer access tokens.",
		obj(NAME, ["name"]),
		True,
	),
	"esign_create_draft": (
		"Create an editable draft, never send. Supply exactly one of content, pdf_file or template_name. Select real contacts with the ERPNext contact tools first. This creates a new document each time; do not blindly retry after an uncertain response—look up the draft first.",
		obj(
			{"data": DATA, "content": CONTENT, "pdf_file": STRING, "template_name": STRING, "fields": FIELDS},
			["data"],
		),
		False,
	),
	"esign_update_draft": (
		"Update only an existing Draft. Read it first. Optional content regenerates its PDF; fields replaces all signing fields. Never edit a document after a signature.",
		obj({**NAME, "data": DATA, "content": CONTENT, "fields": FIELDS}, ["name", "data"]),
		False,
	),
	"esign_send_document": (
		"Send a reviewed draft for signature ONLY when the user explicitly authorizes sending to its recipients. This queues invitation emails. Repeating for an already-sent document does not resend invitations.",
		obj(NAME, ["name"]),
		False,
	),
	"esign_revise_unsigned": (
		"Create a new draft revision of a sent but entirely unsigned document. Invalidates the old signing links. Use only when the user requests revision; the new draft must be sent separately.",
		obj(NAME, ["name"]),
		False,
	),
}


def definitions():
	return [
		{
			"name": name,
			"description": desc,
			"inputSchema": schema,
			"annotations": {
				"readOnlyHint": read,
				"destructiveHint": name in ("esign_update_draft", "esign_revise_unsigned"),
				"idempotentHint": read or name == "esign_send_document",
				"openWorldHint": name == "esign_send_document",
			},
		}
		for name, (desc, schema, read) in TOOLS.items()
	]


def with_url(result):
	name = result.get("name") or result.get("envelope", {}).get("name")
	return (
		{**result, "editor_url": frappe.utils.get_url("/nesscale-sign/document/" + quote(name, safe=""))}
		if name
		else result
	)


def prepare(content, data):
	content = copy.deepcopy(content)
	# The title displayed in the editor and the rendered variable must agree.
	values = [v for v in content.get("resolvedVariables", []) if v.get("key") != "document.title"]
	values.append({"key": "document.title", "value": data.get("title") or "New Document"})
	content["resolvedVariables"] = values
	pdf = builder.render(content, source_pdf=content.get("sourcePdf") if content.get("imported") else None)
	return {**data, "pdf_file": pdf["file_url"], "builder_json": json.dumps(content)}


def execute(name, arguments):
	if frappe.session.user == "Guest":
		frappe.throw("Sign in to use document tools.", frappe.PermissionError)
	if name not in TOOLS:
		frappe.throw("Unknown e-sign tool.")
	try:
		validate(arguments, TOOLS[name][1])
	except ValidationError as exc:
		frappe.throw(
			"Invalid tool input at " + ".".join(str(p) for p in exc.absolute_path) + ": " + exc.validator
		)
	args = copy.deepcopy(arguments)
	if name == "esign_builder_guide":
		frappe.has_permission("NS Envelope", "read", throw=True)
		return guide()
	if name == "esign_list_templates":
		return frappe.get_list(
			"NS Template",
			fields=["name", "title", "status"],
			filters={"title": ["like", "%" + args.get("search", "") + "%"]},
			limit_page_length=100,
		)
	if name == "esign_get_template":
		return template.get_template(**args)
	if name == "esign_list_documents":
		return envelope.list_envelopes(**args)
	if name == "esign_get_document":
		return with_url(envelope.get_envelope(**args))
	if name == "esign_create_draft":
		frappe.has_permission("NS Envelope", "create", throw=True)
		if sum(k in args for k in ("content", "pdf_file", "template_name")) != 1:
			frappe.throw("Choose exactly one of content, pdf_file or template_name.")
		data = args["data"]
		data["title"] = data.get("title") or "New Document"
		if "template_name" in args:
			if "fields" in args:
				frappe.throw("Template fields are inherited; update the draft to replace them.")
			result = envelope.create_from_template(args["template_name"], data)
		else:
			data = (
				prepare(args["content"], data)
				if "content" in args
				else {**data, "pdf_file": args["pdf_file"]}
			)
			data["fields"] = args.get("fields", [])
			result = envelope.create_adhoc(data)
		return with_url(result)
	if name == "esign_update_draft":
		doc = frappe.get_doc("NS Envelope", args["name"])
		doc.check_permission("write")
		lock_envelope(doc.name)
		doc.reload()
		if doc.status != "Draft":
			frappe.throw("Only draft documents can be edited.")
		data = args["data"]
		if "content" not in args and "title" in data and doc.builder_json:
			args["content"] = json.loads(doc.builder_json)
		if "content" in args:
			data = prepare(args["content"], {**data, "title": data.get("title", doc.title)})
		result = envelope.update_envelope(doc.name, data)
		if "fields" in args:
			envelope.save_envelope_fields(doc.name, args["fields"])
		return with_url(result)
	if name == "esign_send_document":
		doc = frappe.get_doc("NS Envelope", args["name"])
		doc.check_permission("write")
		lock_envelope(doc.name)
		doc.reload()
		if doc.status in ("Sent", "In Progress", "Completed"):
			return {"name": doc.name, "status": doc.status, "already_sent": True}
		return with_url(envelope.send_envelope(doc.name))
	return with_url(envelope.revise_unsigned(**args))


def guide():
	return {
		"workflow": [
			"Read an existing template or prepare content and select ERPNext contacts.",
			"Create a draft; inspect its editor_url and PDF before sending.",
			"Send only on user instruction. Never create signatures or change signature status through record updates.",
		],
		"geometry": "Content uses PDF points from the top-left on 595x842 A4 pages. All blocks must fit; text overflow is rejected. Field coordinates use fractions of page dimensions. Imported PDFs require content.imported=true and sourcePdf to reference an authorized private file.",
		"limits": "20 created pages, 200 content blocks, 500 signing fields. Use the existing PDF upload UI to upload files, then pass their private file URL.",
		"variables": "resolvedVariables: [{key:'contact.name',value:'Actual selected contact name'}]. Write {{contact.name}} in text. Missing referenced values are errors. Supply real values from readable records; do not invent contact details.",
		"example": {
			"data": {
				"title": "Service agreement",
				"signers": [
					{
						"role_key": "client",
						"signer_name": "Example Person",
						"signer_email": "example@example.test",
					}
				],
			},
			"content": {
				"layout": "flow",
				"pages": [
					{
						"blocks": [
							{
								"id": "intro",
								"type": "Text",
								"text": "Service agreement",
								"html": "<h2>Service agreement</h2><p>Describe the agreed services here.</p>",
								"x": 38,
								"y": 40,
								"width": 519,
								"height": 140,
								"font_size": 16,
								"padding": 10,
							},
							{
								"id": "signature-block",
								"type": "Field",
								"field_key": "client-signature",
								"padding": 10,
							},
						]
					}
				],
			},
			"fields": [
				{
					"field_key": "client-signature",
					"field_type": "Signature",
					"signer_role": "client",
					"page": 1,
					"pos_x": 0.08,
					"pos_y": 0.3,
					"width": 0.4,
					"height": 0.08,
					"required": 1,
				}
			],
		},
	}
