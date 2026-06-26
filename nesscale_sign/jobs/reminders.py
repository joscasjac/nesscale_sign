# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Reminder engine.

A daily scheduler pass nudges signers who still need to act, respecting each
organisation's reminder interval and maximum-reminder cap. Reminders can also be
triggered manually from the UI (``manual=True`` bypasses interval/cap checks).
"""

import frappe
from frappe.utils import add_to_date, cint, now_datetime

from nesscale_sign.services.audit_service import AuditService
from nesscale_sign.services.notification_service import NotificationService
from nesscale_sign.services.workflow_service import WorkflowService
from nesscale_sign.utils.constants import AuditAction, EnvelopeStatus


def send_reminders():
	"""Scheduler entry point: enqueue reminders for all eligible envelopes."""
	envelopes = frappe.get_all(
		"NS Envelope",
		filters={"status": ["in", [EnvelopeStatus.SENT, EnvelopeStatus.IN_PROGRESS]]},
		pluck="name",
	)
	for name in envelopes:
		frappe.enqueue(
			"nesscale_sign.jobs.reminders.remind_envelope",
			queue="long",
			name=name,
			manual=False,
			job_id=f"ns-reminder-{name}",
		)


def remind_envelope(name: str, manual: bool = False) -> int:
	envelope = frappe.get_doc("NS Envelope", name)
	if envelope.status not in (EnvelopeStatus.SENT, EnvelopeStatus.IN_PROGRESS):
		return 0

	interval, max_count = _reminder_policy(envelope)

	if not manual:
		if not _interval_elapsed(envelope, interval):
			return 0
		if cint(envelope.reminder_count) >= max_count:
			return 0

	active = WorkflowService(envelope).active_signers()
	notifier = NotificationService(envelope)
	sent = 0
	for signer in active:
		notifier.send_reminder(signer)
		AuditService(name).log(AuditAction.REMINDED, signer_email=signer.signer_email,
			details="Manual reminder" if manual else "Scheduled reminder")
		sent += 1

	if sent:
		envelope.db_set("reminder_count", cint(envelope.reminder_count) + 1)
		envelope.db_set("last_reminder_on", now_datetime())
	return sent


def _reminder_policy(envelope) -> tuple[int, int]:
	interval, max_count = 3, 3
	if envelope.organization:
		org = frappe.db.get_value(
			"NS Organization", envelope.organization,
			["reminder_enabled", "reminder_interval_days", "reminder_max_count"],
			as_dict=True,
		)
		if org:
			if not org.reminder_enabled:
				return (0, 0)
			interval = cint(org.reminder_interval_days) or interval
			max_count = cint(org.reminder_max_count) or max_count
	return (interval, max_count)


def _interval_elapsed(envelope, interval_days: int) -> bool:
	if interval_days <= 0:
		return False
	anchor = envelope.last_reminder_on or envelope.sent_on
	if not anchor:
		return False
	return now_datetime() >= add_to_date(anchor, days=interval_days)
