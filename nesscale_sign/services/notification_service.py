# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Email notification service.

All mail is dispatched through the Frappe Email Queue (``frappe.sendmail``).
Bodies are rendered from editable ``Email Template`` records (seeded by
:mod:`nesscale_sign.email.seed`) using Frappe's own template helper, so wording
can be customised from Desk without code changes. Every send is recorded as an
``NS Notification`` row.
"""

import frappe
from frappe.email.doctype.email_template.email_template import get_email_template
from frappe.utils import format_datetime, get_url, now_datetime

from nesscale_sign.email.seed import TEMPLATE_NAMES
from nesscale_sign.services.mail_options import attachment_docs, plain_message


def signing_url(token: str) -> str:
	base = frappe.db.get_single_value("NS Settings", "public_base_url") or get_url()
	return f"{base.rstrip('/')}/sign/{token}"


def app_url(path: str = "") -> str:
	base = get_url()
	return f"{base.rstrip('/')}/nesscale-sign/{path.lstrip('/')}"


class NotificationService:
	def __init__(self, envelope: "frappe.Document"):
		self.envelope = envelope
		# Branding is fixed for now; white-label (custom brand/logo) comes later.
		self.brand = "Open E-Sign ERPNext"

	# --------------------------------------------------------------- public
	def send_invitation(self, signer):
		ctx = self._signer_context(signer)
		rendered = self._render("Invitation", ctx)
		subject = self.envelope.email_subject or rendered["subject"]
		body = (
			plain_message(self.envelope.email_message) if self.envelope.email_message else rendered["message"]
		)
		# The invitation must retain its signer-specific link even with custom wording.
		body += (
			'<p><a href="' + frappe.utils.escape_html(ctx["sign_url"]) + '">Review and sign document</a></p>'
		)
		self._dispatch(signer.signer_email, subject, body, "Invitation", signer.signer_email)

	def send_reminder(self, signer):
		ctx = self._signer_context(signer)
		rendered = self._render("Reminder", ctx)
		self._dispatch(
			signer.signer_email, rendered["subject"], rendered["message"], "Reminder", signer.signer_email
		)

	def send_completed(self):
		ctx = self._base_context()
		ctx["download_url"] = app_url(f"envelopes/{self.envelope.name}")
		rendered = self._render("Completed", ctx)
		for recipient in self._sender_and_signers():
			self._dispatch(recipient, rendered["subject"], rendered["message"], "Completed", recipient)

	def send_declined(self, declined_by: str | None = None, reason: str | None = None):
		ctx = self._base_context()
		ctx.update({"declined_by": declined_by, "reason": reason})
		rendered = self._render("Declined", ctx)
		for recipient in self._sender_and_signers():
			self._dispatch(recipient, rendered["subject"], rendered["message"], "Declined", recipient)

	def send_expired(self):
		rendered = self._render("Expired", self._base_context())
		for recipient in self._sender_and_signers():
			self._dispatch(recipient, rendered["subject"], rendered["message"], "Expired", recipient)

	def send_voided(self, reason: str | None = None):
		ctx = self._base_context()
		ctx["reason"] = reason
		rendered = self._render("Voided", ctx)
		for recipient in self._sender_and_signers():
			self._dispatch(recipient, rendered["subject"], rendered["message"], "Voided", recipient)

	# --------------------------------------------------------------- internals
	def _render(self, notification_type: str, context: dict) -> dict:
		"""Render an Email Template, falling back to a minimal body if missing."""
		template_name = (
			self.envelope.get("email_template") if notification_type == "Invitation" else None
		) or TEMPLATE_NAMES.get(notification_type)
		try:
			return get_email_template(template_name, context)
		except frappe.DoesNotExistError:
			title = context.get("title") or self.envelope.title
			return {
				"subject": f"{notification_type}: {title}",
				"message": f"<p>{notification_type} — {frappe.utils.escape_html(title)}</p>",
			}

	def _dispatch(self, recipient, subject, message, notification_type, signer_email=None):
		notification = frappe.get_doc(
			{
				"doctype": "NS Notification",
				"envelope": self.envelope.name,
				"notification_type": notification_type,
				"recipient": recipient,
				"signer_email": signer_email,
				"subject": subject,
				"status": "Pending",
			}
		)
		notification.flags.ignore_permissions = True
		notification.insert(ignore_permissions=True)
		try:
			frappe.sendmail(
				recipients=[recipient],
				subject=subject,
				message=message,
				reference_doctype="NS Envelope",
				reference_name=self.envelope.name,
				now=False,
				attachments=attachment_docs(self.envelope.get("email_attachments"))
				if notification_type == "Invitation"
				else None,
			)
			notification.db_set("status", "Sent")
			notification.db_set("sent_on", now_datetime())
		except Exception as exc:  # pragma: no cover - mail backend dependent
			notification.db_set("status", "Failed")
			notification.db_set("error", str(exc)[:140])
			frappe.log_error(
				title="Open E-Sign ERPNext: notification failed",
				message=f"Notification {notification.name} failed: {exc}\n\n{frappe.get_traceback()}",
			)

	def _signer_context(self, signer) -> dict:
		ctx = self._base_context()
		ctx.update(
			{
				"signer_name": signer.signer_name,
				"signer_email": signer.signer_email,
				"sign_url": signing_url(signer.token),
				"role": signer.role_label,
			}
		)
		return ctx

	def _base_context(self) -> dict:
		return {
			"brand": self.brand,
			"title": self.envelope.title,
			"sender_name": self.envelope.sender_name,
			"sender_email": self.envelope.sender_email,
			"message": self.envelope.message,
			"expires_on": format_datetime(self.envelope.expires_on) if self.envelope.expires_on else None,
		}

	def _sender_and_signers(self) -> list[str]:
		emails = {s.signer_email for s in self.envelope.signers if s.signer_email}
		if self.envelope.sender_email:
			emails.add(self.envelope.sender_email)
		return sorted(emails)
