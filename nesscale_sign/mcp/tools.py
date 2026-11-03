"""Permission-checked assistant actions using the same services as the editor."""

import copy
import json
from urllib.parse import quote

import frappe
from jsonschema import ValidationError, validate

from nesscale_sign.api import builder, envelope, template
from nesscale_sign.mcp.catalog import (
	CONTENT,
	DATA,
	DESTRUCTIVE_TOOLS,
	EXTENSIONS,
	EXTERNAL_TOOLS,
	FIELDS,
	MANAGER_TOOLS,
	NAME,
	PAGING,
	STRING,
	obj,
)
from nesscale_sign.utils.security import lock_envelope

TOOLS = {
	"esign_builder_guide": (
		"Read the document builder format before creating a document. For the full ERPNext e-sign workflow, start with esign_workflow_guide. No changes.",
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
		"Create a signable ERPNext document, contract, NDA or contractor agreement as an editable Nesscale Sign/Open E-Sign draft; never send. For the complete workflow, read esign_workflow_guide first. Supply exactly one of content, pdf_file or template_name. Select real contacts with the ERPNext contact tools first. This creates a new document each time; do not blindly retry after an uncertain response—look up the draft first.",
		obj(
			{"data": DATA, "content": CONTENT, "pdf_file": STRING, "template_name": STRING, "fields": FIELDS},
			["data"],
		),
		False,
	),
	"esign_update_draft": (
		"Update only an existing Draft. Read it first. Optional content regenerates its PDF; fields replaces all signing fields. Never edit a document after a signature.",
		obj(
			{
				**NAME,
				"data": obj(
					{
						**{k: v for k, v in DATA["properties"].items() if k != "organization"},
						"pdf_file": STRING,
					}
				),
				"content": CONTENT,
				"fields": FIELDS,
			},
			["name", "data"],
		),
		False,
	),
	"esign_send_document": (
		"Send a reviewed ERPNext contract, NDA or document for electronic signature through Nesscale Sign/Open E-Sign ONLY when the user explicitly authorizes sending to its recipients. Read esign_workflow_guide for the complete workflow, and verify the draft with esign_get_document before sending. This queues invitation emails. Repeating for an already-sent document does not resend invitations.",
		obj(NAME, ["name"]),
		False,
	),
	"esign_revise_unsigned": (
		"Create a new draft revision of a sent but entirely unsigned document. Invalidates the old signing links. Use only when the user requests revision; the new draft must be sent separately.",
		obj(NAME, ["name"]),
		False,
	),
}


TOOLS.update({name: (desc, schema, read) for name, (_, desc, schema, read) in EXTENSIONS.items()})
TOOLS["esign_list_templates"] = (TOOLS["esign_list_templates"][0], obj(PAGING), True)


def definitions():
	return [
		{
			"name": name,
			"description": desc,
			"inputSchema": schema,
			"annotations": {
				"readOnlyHint": read,
				"destructiveHint": name in DESTRUCTIVE_TOOLS,
				"idempotentHint": read or name == "esign_send_document",
				"openWorldHint": name in EXTERNAL_TOOLS,
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
		return template.list_templates(**args)
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
	if name == "esign_revise_unsigned":
		return with_url(envelope.revise_unsigned(**args))
	if name in EXTENSIONS:
		from importlib import import_module

		from nesscale_sign.api import require_manager

		if name in MANAGER_TOOLS:
			require_manager()
		path = EXTENSIONS[name][0]
		module, method = path.rsplit(".", 1)
		return getattr(import_module("nesscale_sign." + module), method)(**args)
	frappe.throw("Unknown e-sign tool.")


def guide():
	return {
		"workflow": [
			"Read an existing template, upload a PDF, or prepare builder content; select ERPNext contacts using esign_search_contacts.",
			"Create a draft; inspect its editor_url and PDF before sending.",
			"Send only on user instruction. Never create signatures or change signature status through record updates.",
		],
		"geometry": "Content uses PDF points from the top-left on 595x842 A4 pages. All blocks must fit; text overflow is rejected. Field coordinates use fractions of page dimensions. Imported PDFs require content.imported=true and sourcePdf to reference an authorized private file.",
		"limits": "20 created pages, 200 content blocks, 500 signing fields. Use esign_upload_pdf (base64, max 15 MiB/100 pages), then pass its private file_url. Downloads use bounded base64 chunks; decode chunks separately. Use esign_upload_image for PNG/JPEG builder assets.",
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
