# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Envelope lifecycle service — the orchestration core.

Builds envelopes from templates (or ad-hoc PDFs), sends them, drives the
signing workflow, finalises the immutable signed PDF + certificate, and emits
notifications, audit entries and webhooks at each transition.
"""

import json

import frappe
from frappe import _
from frappe.utils import add_to_date, cint, now_datetime

from nesscale_sign.services import pdf_service
from nesscale_sign.services.audit_service import AuditService
from nesscale_sign.services.notification_service import NotificationService
from nesscale_sign.services.template_service import TemplateService
from nesscale_sign.services.workflow_service import WorkflowService
from nesscale_sign.utils import files
from nesscale_sign.utils.constants import (
	DEFAULT_SIGNER_PALETTE,
	AuditAction,
	EnvelopeStatus,
	SignerStatus,
)
from nesscale_sign.utils.security import digest, lock_envelope, validate_fields

ENVELOPE_FIELD_ATTRS = [
	"field_key",
	"field_type",
	"label",
	"signer_role",
	"page",
	"pos_x",
	"pos_y",
	"width",
	"height",
	"required",
	"read_only",
	"options",
	"default_value",
	"font_size",
	"font_family",
	"repeat_group",
	"mapping_key",
]


class EnvelopeService:
	def __init__(self, envelope: str | None = None):
		self.envelope = envelope

	def _doc(self) -> "frappe.Document":
		return frappe.get_doc("NS Envelope", self.envelope)

	# --------------------------------------------------------------- creation
	@classmethod
	def create_from_template(cls, template: str, data: dict) -> "frappe.Document":
		tmpl = frappe.get_doc("NS Template", template)
		tmpl.check_permission("read")
		if not tmpl.pdf_file:
			frappe.throw(_("Template has no PDF document."))

		env = frappe.new_doc("NS Envelope")
		env.title = data.get("title") or tmpl.title
		env.organization = tmpl.organization
		env.template = tmpl.name
		env.template_version = tmpl.current_version
		env.routing_type = data.get("routing_type") or tmpl.routing_type
		env.source_pdf = tmpl.pdf_file
		env.page_count = tmpl.page_count
		env.email_subject = data.get("email_subject") or tmpl.email_subject
		env.email_message = data.get("email_message") or tmpl.email_message
		env.builder_json = data.get("builder_json") or tmpl.get("builder_json")
		env.email_template = data.get("email_template")
		env.email_attachments = data.get("email_attachments")
		for option in (
			"email_from_name",
			"email_mode",
			"email_from_account",
			"completion_redirect_url",
			"completion_redirect_target",
		):
			env.set(option, data.get(option))
		env.message = data.get("message")
		env.expires_on = data.get("expires_on")
		cls._apply_signers(env, data.get("signers") or [], tmpl)

		# Optional reference document (for field prefill + reversal linkage).
		source_doc = _resolve_source_doc(data.get("source_doctype"), data.get("source_name"))
		if source_doc:
			env.metadata_json = json.dumps({"ref_doctype": source_doc.doctype, "ref_name": source_doc.name})
		env.insert()

		svc = cls(env.name)
		template_fields = TemplateService(tmpl.name).get_fields()
		svc._materialise_fields(env, template_fields, source_doc=source_doc)
		AuditService(env.name).log(AuditAction.CREATED, details=f"From template {tmpl.name}")
		return frappe.get_doc("NS Envelope", env.name)

	@classmethod
	def create_adhoc(cls, data: dict) -> "frappe.Document":
		"""Create an envelope from a directly uploaded PDF + inline field layout."""
		if not data.get("pdf_file"):
			frappe.throw(_("A PDF file is required."))
		content = files.read_authorized_pdf(data["pdf_file"])

		env = frappe.new_doc("NS Envelope")
		env.title = data.get("title") or _("Untitled Document")
		env.organization = data.get("organization") or _default_org()
		env.routing_type = data.get("routing_type") or "Sequential"
		env.source_pdf = data["pdf_file"]
		env.page_count = pdf_service.get_page_count(content)
		env.email_subject = data.get("email_subject")
		env.email_message = data.get("email_message")
		env.builder_json = data.get("builder_json")
		env.email_template = data.get("email_template")
		env.email_attachments = data.get("email_attachments")
		for option in (
			"email_from_name",
			"email_mode",
			"email_from_account",
			"completion_redirect_url",
			"completion_redirect_target",
		):
			env.set(option, data.get(option))
		env.message = data.get("message")
		env.expires_on = data.get("expires_on")
		source_doc = _resolve_source_doc(data.get("source_doctype"), data.get("source_name"))
		if source_doc:
			env.metadata_json = json.dumps({"ref_doctype": source_doc.doctype, "ref_name": source_doc.name})
		cls._apply_signers(env, data.get("signers") or [], None)
		env.insert()

		cls(env.name)._materialise_fields(env, data.get("fields") or [])
		AuditService(env.name).log(AuditAction.CREATED, details="Ad-hoc envelope")
		return frappe.get_doc("NS Envelope", env.name)

	@staticmethod
	def _apply_signers(env, signers: list[dict], tmpl):
		env.set("signers", [])
		for idx, s in enumerate(signers):
			env.append(
				"signers",
				{
					"signer_name": s.get("signer_name") or s.get("name"),
					"signer_email": (s.get("signer_email") or s.get("email") or "").strip().lower(),
					"role_key": s.get("role_key"),
					"role_label": s.get("role_label") or s.get("role"),
					"signing_order": cint(s.get("signing_order")) or (idx + 1),
					"color": s.get("color") or DEFAULT_SIGNER_PALETTE[idx % len(DEFAULT_SIGNER_PALETTE)],
					"auth_method": s.get("auth_method") or "None",
					"status": SignerStatus.PENDING,
				},
			)

	def _materialise_fields(self, env, source_fields: list[dict], source_doc=None):
		"""Snapshot template/inline fields into per-envelope ``NS Envelope Field`` rows.

		Fields carrying a ``mapping_key`` are prefilled (and locked) from the
		reference document when one is supplied.
		"""
		validate_fields(source_fields, env.page_count or 0)
		role_to_email = {(s.role_key or "").lower(): s.signer_email for s in env.signers if s.role_key}
		# Fallback: single-signer envelopes bind every field to that signer.
		default_email = env.signers[0].signer_email if len(env.signers) == 1 else None

		for field in source_fields:
			role_key = (field.get("signer_role") or "").lower()
			signer_email = role_to_email.get(role_key) if role_key else default_email
			row = frappe.new_doc("NS Envelope Field")
			row.envelope = env.name
			row.signer_email = signer_email
			for attr in ENVELOPE_FIELD_ATTRS:
				if field.get(attr) is not None:
					row.set(attr, field.get(attr))
			if not row.field_key:
				row.field_key = frappe.generate_hash(length=10)
			if field.get("field_type") not in ("Signature", "Initial", "Stamp", "Date Signed") and field.get(
				"default_value"
			) not in (None, ""):
				row.value = field.get("default_value")
				row.filled = 1
			mapped = _read_mapped_value(source_doc, field.get("mapping_key"))
			if mapped not in (None, ""):
				row.value = mapped
				row.filled = 1
				row.read_only = 1
			row.flags.ignore_permissions = True
			row.insert(ignore_permissions=True)

	def remap_field_signers(self):
		"""Re-point each envelope field to its role's (possibly newly filled)
		signer email. Used after a Draft envelope's signers are edited."""
		env = self._doc()
		role_to_email = {(s.role_key or "").lower(): s.signer_email for s in env.signers if s.role_key}
		default_email = env.signers[0].signer_email if len(env.signers) == 1 else None
		for f in frappe.get_all(
			"NS Envelope Field", filters={"envelope": env.name}, fields=["name", "signer_role"]
		):
			email = role_to_email.get((f.signer_role or "").lower()) if f.signer_role else default_email
			frappe.db.set_value("NS Envelope Field", f.name, "signer_email", email, update_modified=False)

	# --------------------------------------------------------------- send
	def send(self) -> "frappe.Document":
		lock_envelope(self.envelope)
		env = self._doc()
		self._validate_sendable(env)
		from nesscale_sign.services.mail_options import attachment_docs, validate_options

		validate_options(env)
		attached = attachment_docs(env.get("email_attachments"), check_permission=True)
		snapshots = [
			files.save_private_file(
				a["fname"], a["fcontent"], attached_to_doctype="NS Envelope", attached_to_name=env.name
			).name
			for a in attached
		]
		env.email_attachments = json.dumps(snapshots)
		content = files.read_authorized_pdf(env.source_pdf)
		snapshot = files.save_private_file(
			f"{env.name}-original.pdf", content, attached_to_doctype="NS Envelope", attached_to_name=env.name
		)
		env.source_pdf = snapshot.file_url
		env.source_sha256 = digest(content)

		for signer in env.signers:
			if not signer.token:
				signer.token = frappe.generate_hash(length=40)

		if not env.expires_on:
			days = _expiry_days(env)
			if days:
				env.expires_on = add_to_date(now_datetime(), days=days)

		env.status = EnvelopeStatus.SENT
		env.sent_on = now_datetime()

		workflow = WorkflowService(env)
		workflow.envelope.current_order = workflow.current_order() or 0
		to_notify = workflow.signers_to_activate_on_send()
		workflow.mark_sent(to_notify)
		env.flags.esign_transition = True
		env.save()

		notifier = NotificationService(env)
		for signer in to_notify:
			notifier.send_invitation(signer)

		AuditService(env.name).log(AuditAction.SENT, details=f"Sent to {len(to_notify)} signer(s)")
		return frappe.get_doc("NS Envelope", env.name)

	def _validate_sendable(self, env):
		if env.status != EnvelopeStatus.DRAFT:
			frappe.throw(_("Only draft envelopes can be sent."))
		if not env.signers:
			frappe.throw(_("Add at least one signer before sending."))
		seen = set()
		for signer in env.signers:
			if signer.signer_email in seen:
				frappe.throw(_("Each signer must have a unique email address."))
			seen.add(signer.signer_email)
			if not signer.signer_email:
				frappe.throw(_("Every signer needs an email address."))
			frappe.utils.validate_email_address(signer.signer_email, throw=True)
			if signer.auth_method not in (None, "", "None"):
				frappe.throw(_("Only email-link authentication is currently supported."))

		roles = {(s.role_key or "").lower() for s in env.signers}
		for field in frappe.get_all(
			"NS Envelope Field",
			filters={"envelope": env.name},
			fields=["signer_role", "signer_email", "field_type"],
		):
			if field.signer_role and field.signer_role.lower() not in roles:
				frappe.throw(_("Reassign fields belonging to a removed recipient before sending."))
			if field.field_type != "Label" and field.signer_email not in seen:
				frappe.throw(_("Assign every signing field to a recipient before sending."))

	# --------------------------------------------------------------- resend
	def resend(self, signer_email: str) -> "frappe.Document":
		env = self._doc()
		signer = env.get_signer(signer_email)
		if not signer:
			frappe.throw(_("Signer not found."))
		if signer.status == SignerStatus.SIGNED:
			frappe.throw(_("Signer has already signed."))
		NotificationService(env).send_invitation(signer)
		signer.db_set("sent_on", now_datetime())
		AuditService(env.name).log(AuditAction.REMINDED, signer_email=signer_email, details="Manual resend")
		return env

	# --------------------------------------------------------------- void
	def void(self, reason: str | None = None) -> "frappe.Document":
		env = self._doc()
		if env.status in EnvelopeStatus.TERMINAL:
			frappe.throw(_("Envelope is already in a final state."))
		env.status = EnvelopeStatus.VOIDED
		env.voided_on = now_datetime()
		env.void_reason = reason
		env.flags.esign_transition = True
		env.save()
		NotificationService(env).send_voided(reason)
		AuditService(env.name).log(AuditAction.VOIDED, details=reason)
		return env

	# --------------------------------------------------------------- finalize
	def finalize(self) -> "frappe.Document":
		"""Generate the immutable signed PDF + certificate and complete the envelope."""
		lock_envelope(self.envelope)
		env = self._doc()
		if env.status == "Completed":
			return env
		if (
			env.status not in ("Sent", "In Progress")
			or not env.signers
			or not all(s.status == "Signed" for s in env.signers)
		):
			frappe.throw(_("Only fully signed documents can be completed."))
		source = files.read_file_content(env.source_pdf)
		if not env.source_sha256 or digest(source) != env.source_sha256:
			frappe.throw(_("The original document has changed. Completion was stopped."))

		fields = frappe.get_all(
			"NS Envelope Field",
			filters={"envelope": env.name},
			fields=[
				"name",
				"field_key",
				"field_type",
				"label",
				"page",
				"pos_x",
				"pos_y",
				"width",
				"height",
				"value",
				"signature",
				"font_size",
				"font_family",
			],
			limit_page_length=0,
		)
		signature_images: dict[str, bytes] = {}
		for field in fields:
			if field.get("signature"):
				img_url = frappe.db.get_value("NS Signature", field["signature"], "signature_image")
				if img_url:
					signature_images[field["field_key"]] = files.read_file_content(img_url)

		filled = pdf_service.generate_filled_pdf(source, fields, signature_images)

		from nesscale_sign.services.seal_service import seal_pdf

		env.status = EnvelopeStatus.COMPLETED
		env.completed_on = now_datetime()
		env.finalization_status = "Complete"
		env.finalization_error = None
		AuditService(env.name).log(AuditAction.COMPLETED, details="All signers completed")
		chain = AuditService(env.name).verify()
		if not chain["valid"]:
			frappe.throw(_("Audit integrity check failed. Completion was stopped."))
		certificate = pdf_service.build_certificate(env, AuditService(env.name).list(), chain, embedded=True)
		# Append before sealing: rewriting a sealed PDF would invalidate its signature.
		filled = pdf_service.append_certificate(filled, certificate)
		filled, env.seal_status = seal_pdf(filled)
		env.signed_sha256 = digest(filled)
		AuditService(env.name).log(AuditAction.GENERATED, details=f"PDF SHA-256: {env.signed_sha256}")
		certificate, _certificate_seal_status = seal_pdf(certificate)
		for field, suffix, content in (
			("signed_pdf", "signed", filled),
			("certificate_pdf", "certificate", certificate),
		):
			file = files.save_private_file(
				f"{env.name}-{suffix}.pdf",
				content,
				attached_to_doctype="NS Envelope",
				attached_to_name=env.name,
				attached_to_field=field,
			)
			env.set(field, file.file_url)
		env.recompute_progress()
		env.flags.esign_transition = True
		env.save(ignore_permissions=True)

		# Attach completion artifacts to the source record selected by the sender.
		meta = json.loads(env.metadata_json or "{}")
		if (
			meta.get("ref_doctype")
			and meta.get("ref_name")
			and frappe.db.exists(meta["ref_doctype"], meta["ref_name"])
		):
			for url, suffix in ((env.signed_pdf, "signed"), (env.certificate_pdf, "certificate")):
				files.save_private_file(
					f"{env.name}-{suffix}.pdf",
					files.read_file_content(url),
					attached_to_doctype=meta["ref_doctype"],
					attached_to_name=meta["ref_name"],
				)
		NotificationService(env).send_completed()
		return frappe.get_doc("NS Envelope", env.name)

	# --------------------------------------------------------------- expiry
	def expire(self) -> "frappe.Document":
		env = self._doc()
		if env.status in EnvelopeStatus.TERMINAL:
			return env
		env.status = EnvelopeStatus.EXPIRED
		env.flags.esign_transition = True
		env.save()
		NotificationService(env).send_expired()
		AuditService(env.name).log(AuditAction.EXPIRED, details="Envelope expired")
		return env


# --------------------------------------------------------------------- helpers
def _default_org() -> str | None:
	return frappe.db.get_single_value("NS Settings", "default_organization")


def _resolve_source_doc(doctype: str | None, name: str | None):
	if not doctype and not name:
		return None
	if not (doctype and name) or not frappe.db.exists(doctype, name):
		frappe.throw(_("Choose an existing reference document and its document type."))
	doc = frappe.get_doc(doctype, name)
	doc.check_permission("write")
	return doc


def _read_mapped_value(source_doc, mapping_key: str | None):
	"""Read a (possibly dotted) field path from the reference document."""
	if not source_doc or not mapping_key:
		return None
	value = source_doc
	for part in str(mapping_key).split("."):
		if value is None:
			return None
		value = value.get(part) if hasattr(value, "get") else getattr(value, part, None)
	if value is None:
		return None
	return value if isinstance(value, str) else str(value)


def _expiry_days(env) -> int | None:
	if env.template:
		days = frappe.db.get_value("NS Template", env.template, "expiry_days")
		if days:
			return cint(days)
	if env.organization:
		days = frappe.db.get_value("NS Organization", env.organization, "default_expiry_days")
		if days:
			return cint(days)
	return 30
