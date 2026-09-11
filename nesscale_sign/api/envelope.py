# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Envelope API endpoints."""

import json

import frappe

from nesscale_sign.api import load
from nesscale_sign.services.audit_service import AuditService
from nesscale_sign.services.envelope_service import EnvelopeService
from nesscale_sign.utils.security import public_envelope


@frappe.whitelist()
def create_from_template(template: str, data=None):
	return public_envelope(EnvelopeService.create_from_template(template, load(data) or {}))


@frappe.whitelist()
def create_adhoc(data: dict | None = None):
	return public_envelope(EnvelopeService.create_adhoc(load(data) or {}))


@frappe.whitelist()
def get_envelope(name: str):
	doc = frappe.get_doc("NS Envelope", name)
	doc.check_permission("read")
	fields = frappe.get_all(
		"NS Envelope Field",
		filters={"envelope": name},
		fields=[
			"name",
			"field_key",
			"field_type",
			"label",
			"signer_email",
			"signer_role",
			"page",
			"pos_x",
			"pos_y",
			"width",
			"height",
			"required",
			"read_only",
			"value",
			"filled",
			"options",
			"font_size",
			"repeat_group",
			"default_value",
			"mapping_key",
			"font_family",
		],
		order_by="page asc, creation asc",
		limit_page_length=0,
	)
	return {
		"envelope": public_envelope(doc),
		"fields": fields,
		"audit": AuditService(name).list(),
	}


@frappe.whitelist()
def list_envelopes(
	status: str | None = None, search: str | None = None, start: int = 0, page_length: int = 20
):
	filters = {}
	if status:
		filters["status"] = status
	or_filters = None
	if search:
		or_filters = {"title": ["like", f"%{search}%"], "name": ["like", f"%{search}%"]}
	return frappe.get_list(
		"NS Envelope",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"title",
			"status",
			"organization",
			"routing_type",
			"progress",
			"sender_name",
			"sent_on",
			"completed_on",
			"expires_on",
			"modified",
		],
		order_by="modified desc",
		start=int(start),
		page_length=int(page_length),
	)


@frappe.whitelist()
def my_pending_signatures():
	"""Documents awaiting the logged-in user's signature.

	Lets a signed-in signer act from inside the app instead of opening the
	email link. Each row carries that user's own signing token (they receive
	the same token by email), which the SPA uses to open the signing page.
	"""
	user_email = frappe.session.user
	if user_email in ("Guest", "Administrator"):
		# Administrator is rarely an actual signer; skip the noisy match.
		if user_email == "Guest":
			return []
	return frappe.db.sql(
		"""
		SELECT e.name, e.title, e.status, e.sender_name, e.sent_on, e.expires_on,
			es.token, es.role_label, es.color, es.status AS signer_status
		FROM `tabNS Envelope Signer` es
		INNER JOIN `tabNS Envelope` e ON e.name = es.parent
		WHERE es.signer_email = %s
			AND es.status IN ('Sent', 'Viewed')
			AND e.status IN ('Sent', 'In Progress')
		ORDER BY e.sent_on DESC
		""",
		(user_email,),
		as_dict=True,
	)


@frappe.whitelist()
def update_envelope(name: str, data=None):
	doc = frappe.get_doc("NS Envelope", name)
	doc.check_permission("write")
	if doc.status != "Draft":
		frappe.throw(frappe._("Only draft envelopes can be edited."))
	data = load(data) or {}
	if data.get("pdf_file") and data["pdf_file"] != doc.source_pdf:
		from nesscale_sign.services.pdf_service import get_page_count
		from nesscale_sign.utils.files import read_authorized_pdf

		doc.page_count = get_page_count(read_authorized_pdf(data["pdf_file"]))
		doc.source_pdf = data["pdf_file"]
	for field in (
		"title",
		"routing_type",
		"email_subject",
		"email_message",
		"message",
		"expires_on",
		"builder_json",
		"email_template",
		"email_attachments",
	):
		if field in data:
			doc.set(field, data[field])
	if "source_doctype" in data or "source_name" in data:
		from nesscale_sign.services.envelope_service import _resolve_source_doc

		source = _resolve_source_doc(data.get("source_doctype"), data.get("source_name"))
		doc.metadata_json = (
			json.dumps({"ref_doctype": source.doctype, "ref_name": source.name}) if source else None
		)
	if "signers" in data:
		EnvelopeService._apply_signers(doc, data["signers"], None)
	doc.save()
	if "signers" in data:
		EnvelopeService(name).remap_field_signers()
	return public_envelope(doc)


@frappe.whitelist()
def save_envelope_fields(name: str, fields=None):
	"""Replace per-envelope field instances (used by the ad-hoc designer)."""
	doc = frappe.get_doc("NS Envelope", name)
	doc.check_permission("write")
	if doc.status != "Draft":
		frappe.throw(frappe._("Only draft envelopes can be edited."))
	existing = frappe.get_all("NS Envelope Field", filters={"envelope": name}, pluck="name")
	for row in existing:
		frappe.delete_doc("NS Envelope Field", row, ignore_permissions=True, force=True)
	EnvelopeService(name)._materialise_fields(doc, load(fields) or [])
	return {"saved": True}


@frappe.whitelist()
def send_envelope(name: str):
	frappe.get_doc("NS Envelope", name).check_permission("write")
	return public_envelope(EnvelopeService(name).send())


@frappe.whitelist()
def void_envelope(name: str, reason: str | None = None):
	frappe.get_doc("NS Envelope", name).check_permission("write")
	return public_envelope(EnvelopeService(name).void(reason))


@frappe.whitelist()
def resend_envelope(name: str, signer_email: str):
	frappe.get_doc("NS Envelope", name).check_permission("write")
	EnvelopeService(name).resend(signer_email)
	return {"resent": True}


@frappe.whitelist()
def remind_envelope(name: str):
	"""Send a manual reminder to all outstanding signers."""
	from nesscale_sign.jobs.reminders import remind_envelope as _remind

	frappe.get_doc("NS Envelope", name).check_permission("write")
	count = _remind(name, manual=True)
	return {"reminded": count}


@frappe.whitelist()
def get_audit(name: str):
	frappe.get_doc("NS Envelope", name).check_permission("read")
	return {
		"events": AuditService(name).list(),
		"integrity": AuditService(name).verify(),
	}


@frappe.whitelist()
def download_signed(name: str):
	doc = frappe.get_doc("NS Envelope", name)
	doc.check_permission("read")
	if not doc.signed_pdf:
		frappe.throw(frappe._("Signed document is not available yet."))
	AuditService(name).log("Downloaded", details="Signed PDF downloaded")
	_stream_private_file(doc.signed_pdf, f"{doc.name}-signed.pdf")


@frappe.whitelist()
def delete_envelope(name: str):
	doc = frappe.get_doc("NS Envelope", name)
	doc.check_permission("delete")
	if doc.status != "Draft":
		frappe.throw(frappe._("Only draft envelopes can be deleted."))
	frappe.delete_doc("NS Envelope", name)
	return {"deleted": True}


def _stream_private_file(file_url: str, download_name: str):
	from nesscale_sign.utils import files

	content = files.read_file_content(file_url)
	frappe.local.response.filename = download_name
	frappe.local.response.filecontent = content
	frappe.local.response.type = "pdf"
	frappe.local.response.display_content_as = "attachment"


@frappe.whitelist()
def retry_completion(name: str):
	doc = frappe.get_doc("NS Envelope", name)
	doc.check_permission("write")
	from nesscale_sign.services.finalization import schedule_finalization

	schedule_finalization(name)
	return {"status": "processing"}


@frappe.whitelist()
def preview_pdf(name: str):
	doc = frappe.get_doc("NS Envelope", name)
	doc.check_permission("read")
	_stream_private_file(doc.signed_pdf if doc.status == "Completed" else doc.source_pdf, f"{doc.name}.pdf")


@frappe.whitelist()
def download_certificate(name: str):
	doc = frappe.get_doc("NS Envelope", name)
	doc.check_permission("read")
	if not doc.certificate_pdf:
		frappe.throw("The completion record is not ready yet.")
	_stream_private_file(doc.certificate_pdf, f"{doc.name}-certificate.pdf")
