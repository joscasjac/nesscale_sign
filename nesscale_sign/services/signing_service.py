# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Public signing service — token-authenticated, no login required.

Drives the signer-facing flow: resolve a secure token, expose the document and
the signer's fields, capture field values and signatures, then submit. When a
signer completes, the workflow engine decides whether to advance to the next
order, complete the envelope, or wait.
"""

import frappe
from frappe import _
from frappe.utils import get_datetime, now_datetime

from nesscale_sign.services.audit_service import AuditService
from nesscale_sign.services.envelope_service import EnvelopeService
from nesscale_sign.services.notification_service import NotificationService
from nesscale_sign.services.workflow_service import WorkflowService
from nesscale_sign.utils import files, request_meta
from nesscale_sign.utils.constants import (
	AUTO_FIELD_TYPES,
	SIGNATURE_FIELD_TYPES,
	AuditAction,
	EnvelopeStatus,
	SignerStatus,
)
from nesscale_sign.utils.security import CONSENT_TEXT, CONSENT_VERSION, lock_envelope, validate_value


class SigningService:
	def __init__(self, token: str):
		self.token = token
		self.envelope, self.signer = self._resolve(token)

	# --------------------------------------------------------------- resolve
	@staticmethod
	def _resolve(token: str):
		if not token:
			frappe.throw(_("Invalid signing link."), frappe.PermissionError)
		parent = frappe.db.get_value("NS Envelope Signer", {"token": token}, "parent")
		if not parent:
			frappe.throw(_("This signing link is invalid or has expired."), frappe.PermissionError)
		lock_envelope(parent)
		envelope = frappe.get_doc("NS Envelope", parent)
		if envelope.status in ("Draft", "Voided", "Declined", "Expired"):
			frappe.throw(_("This signing link is no longer available."), frappe.PermissionError)
		if (
			envelope.status != "Completed"
			and envelope.expires_on
			and get_datetime(envelope.expires_on) < now_datetime()
		):
			frappe.throw(_("This signing link has expired."), frappe.PermissionError)
		signer = envelope.get_signer_by_token(token)
		return envelope, signer

	def _guard_actionable(self):
		if (
			self.envelope.status in EnvelopeStatus.TERMINAL
			and self.envelope.status != EnvelopeStatus.COMPLETED
		):
			frappe.throw(_("This document is {0} and can no longer be signed.").format(self.envelope.status))
		if self.envelope.expires_on and get_datetime(self.envelope.expires_on) < now_datetime():
			frappe.throw(_("This signing request has expired."))
		if self.signer.status == SignerStatus.SIGNED:
			frappe.throw(_("You have already signed this document."))
		if self.signer.status == SignerStatus.DECLINED:
			frappe.throw(_("You have declined this document."))
		if not WorkflowService(self.envelope).can_sign(self.signer):
			frappe.throw(_("It is not your turn to sign yet. You will be notified when ready."))

	# --------------------------------------------------------------- view
	def get_context(self) -> dict:
		"""Everything the signing UI needs; marks the document as viewed."""
		self._mark_viewed()
		fields = self._signer_fields()
		return {
			"envelope": {
				"name": self.envelope.name,
				"title": self.envelope.title,
				"status": self.envelope.status,
				"page_count": self.envelope.page_count,
				"message": self.envelope.message,
				"sender_name": self.envelope.sender_name,
				"expires_on": self.envelope.expires_on,
				"routing_type": self.envelope.routing_type,
				"finalization_status": self.envelope.finalization_status,
				"seal_status": self.envelope.seal_status,
			},
			"signer": {
				"name": self.signer.signer_name,
				"email": self.signer.signer_email,
				"role_label": self.signer.role_label,
				"color": self.signer.color,
				"status": self.signer.status,
				"can_sign": WorkflowService(self.envelope).can_sign(self.signer),
			},
			"fields": fields,
			"pdf_url": self._signed_token_pdf_url(),
			"consent_text": CONSENT_TEXT,
			"consent_version": CONSENT_VERSION,
		}

	def _signer_fields(self) -> list[dict]:
		rows = frappe.get_all(
			"NS Envelope Field",
			filters={"envelope": self.envelope.name},
			fields=[
				"name",
				"field_key",
				"field_type",
				"label",
				"signer_email",
				"page",
				"pos_x",
				"pos_y",
				"width",
				"height",
				"required",
				"read_only",
				"value",
				"options",
				"default_value",
				"font_size",
				"filled",
				"repeat_group",
			],
			order_by="page asc, creation asc",
			limit_page_length=0,
		)
		signer_email = (self.signer.signer_email or "").lower()
		for row in rows:
			row["editable"] = (row.get("signer_email") or "").lower() == signer_email and not row.get(
				"read_only"
			)
		return rows

	def _signed_token_pdf_url(self) -> str:
		from urllib.parse import quote

		from nesscale_sign.services.notification_service import signing_url

		return f"/api/method/nesscale_sign.api.signing.get_pdf?token={quote(self.token)}"

	def _mark_viewed(self):
		if self.signer.status in (SignerStatus.PENDING, SignerStatus.SENT):
			frappe.db.set_value(
				"NS Envelope Signer",
				self.signer.name,
				{
					"status": SignerStatus.VIEWED,
					"viewed_on": now_datetime(),
					"ip_address": request_meta.get_request_ip(),
					"user_agent": request_meta.get_user_agent(),
				},
				update_modified=False,
			)
			self.signer.status = SignerStatus.VIEWED
			AuditService(self.envelope.name).log(
				AuditAction.VIEWED,
				signer_email=self.signer.signer_email,
				signer_name=self.signer.signer_name,
			)
		self._touch_session()

	def _touch_session(self):
		meta = request_meta.collect()
		existing = frappe.db.get_value(
			"NS Signing Session", {"token": self.token, "status": "Active"}, "name"
		)
		if existing:
			frappe.db.set_value(
				"NS Signing Session", existing, "last_activity", now_datetime(), update_modified=False
			)
			return
		session = frappe.get_doc(
			{
				"doctype": "NS Signing Session",
				"envelope": self.envelope.name,
				"signer_email": self.signer.signer_email,
				"token": self.token,
				"status": "Active",
				"started_on": now_datetime(),
				"last_activity": now_datetime(),
				"expires_on": self.envelope.expires_on,
				**{
					k: meta.get(k) for k in ("ip_address", "country", "browser", "os", "device", "user_agent")
				},
			}
		)
		session.flags.ignore_permissions = True
		session.insert(ignore_permissions=True)
		frappe.db.set_value(
			"NS Envelope Signer", self.signer.name, "signing_session", session.name, update_modified=False
		)

	# --------------------------------------------------------------- pdf bytes
	def get_pdf_bytes(self) -> bytes:
		AuditService(self.envelope.name).log(
			AuditAction.OPENED,
			signer_email=self.signer.signer_email,
			signer_name=self.signer.signer_name,
			details="Opened document",
		)
		return files.read_file_content(self.envelope.source_pdf)

	# --------------------------------------------------------------- save / sign
	def save_values(self, values: dict) -> dict:
		"""Persist field values without finalising (draft progress)."""
		self._guard_actionable()
		self._apply_values(values)
		return {"saved": True}

	def _apply_values(self, values: dict):
		rows = frappe.get_all(
			"NS Envelope Field",
			filters={"envelope": self.envelope.name, "signer_email": self.signer.signer_email},
			fields=["name", "field_key", "field_type", "read_only", "options"],
		)
		if not isinstance(values, dict):
			frappe.throw(_("Invalid field values."))
		for row in rows:
			if (
				row.read_only
				or row.field_type in SIGNATURE_FIELD_TYPES
				or row.field_type in AUTO_FIELD_TYPES
				or row.field_key not in values
			):
				continue
			value = validate_value(row, values[row.field_key])
			frappe.db.set_value(
				"NS Envelope Field",
				row.name,
				{"value": value, "filled": int(value not in (None, "")), "filled_on": now_datetime()},
				update_modified=False,
			)

	def submit(self, values: dict, signature: dict, consent: bool = False) -> dict:
		"""Capture all values + signature artifacts and complete this signer."""
		if self.signer.status == SignerStatus.SIGNED:
			return {
				"status": "completed" if self.envelope.status == "Completed" else "signed",
				"envelope": self.envelope.name,
			}
		self._guard_actionable()
		if consent is not True:
			frappe.throw(_("Please agree to sign electronically."))
		if not isinstance(values, dict) or not isinstance(signature, dict):
			frappe.throw(_("Invalid signing request."))
		meta = request_meta.collect()

		signature_doc = self._capture_signature(signature, meta) if signature else None
		self._fill_signer_fields(values, signature_doc)
		self._validate_required_filled()

		frappe.db.set_value(
			"NS Envelope Signer",
			self.signer.name,
			{
				"status": SignerStatus.SIGNED,
				"signed_on": now_datetime(),
				"consent_version": CONSENT_VERSION,
				"consent_text": CONSENT_TEXT,
				"ip_address": meta.get("ip_address"),
				"user_agent": meta.get("user_agent"),
			},
			update_modified=False,
		)

		AuditService(self.envelope.name).log(
			AuditAction.SIGNED,
			signer_email=self.signer.signer_email,
			signer_name=self.signer.signer_name,
			meta=meta,
			details=f"Consent {CONSENT_VERSION}: {CONSENT_TEXT}",
		)

		self._complete_session()
		return self._advance()

	def _capture_signature(self, signature: dict, meta: dict) -> "frappe.Document":
		sig_type = signature.get("type") or "Draw"
		if sig_type not in ("Draw", "Type", "Upload"):
			frappe.throw(_("Unsupported signature type."))
		image_data = signature.get("image")
		if not image_data:
			frappe.throw(_("A visible signature is required."))
		file_doc = None
		if image_data:
			file_doc = files.save_base64_image(
				f"{self.envelope.name}-{frappe.generate_hash(length=6)}-sign.png",
				image_data,
			)
		doc = frappe.get_doc(
			{
				"doctype": "NS Signature",
				"envelope": self.envelope.name,
				"signer_email": self.signer.signer_email,
				"signer_name": self.signer.signer_name,
				"signature_type": sig_type,
				"signature_image": file_doc.file_url if file_doc else None,
				"typed_text": signature.get("text"),
				"font": signature.get("font"),
				"ip_address": meta.get("ip_address"),
				"user_agent": meta.get("user_agent"),
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		return doc

	def _fill_signer_fields(self, values: dict, signature_doc):
		rows = frappe.get_all(
			"NS Envelope Field",
			filters={"envelope": self.envelope.name, "signer_email": self.signer.signer_email},
			fields=["name", "field_key", "field_type", "read_only", "options"],
		)
		values = values or {}
		for row in rows:
			if row.get("read_only"):
				continue
			ftype = row["field_type"]
			update = {"filled_on": now_datetime()}
			if ftype in SIGNATURE_FIELD_TYPES:
				if signature_doc:
					update["signature"] = signature_doc.name
					update["filled"] = 1
			elif ftype in AUTO_FIELD_TYPES:
				update["value"] = frappe.utils.format_datetime(now_datetime(), "dd MMM yyyy")
				update["filled"] = 1
			elif row["field_key"] in values:
				val = validate_value(row, values[row["field_key"]])
				update["value"] = val
				update["filled"] = 1 if val not in (None, "") else 0
			else:
				continue
			frappe.db.set_value("NS Envelope Field", row["name"], update, update_modified=False)
			if update.get("filled"):
				AuditService(self.envelope.name).log(
					AuditAction.FIELD_FILLED,
					signer_email=self.signer.signer_email,
					details=f"{ftype}:{row['field_key']}",
				)

	def _validate_required_filled(self):
		missing = frappe.get_all(
			"NS Envelope Field",
			filters={
				"envelope": self.envelope.name,
				"signer_email": self.signer.signer_email,
				"required": 1,
				"read_only": 0,
				"filled": 0,
			},
			fields=["label", "field_key"],
		)
		if missing:
			labels = ", ".join(m.get("label") or m.get("field_key") for m in missing)
			frappe.throw(_("Please complete all required fields: {0}").format(labels))

	def _advance(self) -> dict:
		envelope = frappe.get_doc("NS Envelope", self.envelope.name)
		workflow = WorkflowService(envelope)
		result = workflow.handle_signed(envelope.get_signer(self.signer.signer_email))
		envelope.flags.esign_transition = True
		envelope.save(ignore_permissions=True)

		if result["completed"]:
			from nesscale_sign.services.finalization import schedule_finalization

			schedule_finalization(envelope.name)
			return {"status": "processing", "envelope": envelope.name}

		if result["next_signers"]:
			notifier = NotificationService(frappe.get_doc("NS Envelope", envelope.name))
			for signer in result["next_signers"]:
				notifier.send_invitation(signer)
		return {"status": "signed", "envelope": envelope.name}

	# --------------------------------------------------------------- decline
	def decline(self, reason: str | None = None) -> dict:
		self._guard_actionable()
		envelope = frappe.get_doc("NS Envelope", self.envelope.name)
		workflow = WorkflowService(envelope)
		workflow.handle_declined(envelope.get_signer(self.signer.signer_email), reason)
		envelope.flags.esign_transition = True
		envelope.save(ignore_permissions=True)

		AuditService(envelope.name).log(
			AuditAction.DECLINED,
			signer_email=self.signer.signer_email,
			signer_name=self.signer.signer_name,
			details=reason,
		)
		NotificationService(envelope).send_declined(self.signer.signer_name, reason)
		self._complete_session()
		return {"status": "declined", "envelope": envelope.name}

	def _complete_session(self):
		name = frappe.db.get_value("NS Signing Session", {"token": self.token, "status": "Active"}, "name")
		if name:
			frappe.db.set_value(
				"NS Signing Session",
				name,
				{
					"status": "Completed",
					"completed_on": now_datetime(),
				},
				update_modified=False,
			)
