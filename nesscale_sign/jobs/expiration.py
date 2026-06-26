# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Document expiration sweep + signing-session housekeeping."""

import frappe
from frappe.utils import now_datetime

from nesscale_sign.services.envelope_service import EnvelopeService
from nesscale_sign.utils.constants import EnvelopeStatus


def expire_envelopes():
	"""Scheduler entry point: mark past-due envelopes as Expired."""
	due = frappe.get_all(
		"NS Envelope",
		filters={
			"status": ["in", [EnvelopeStatus.SENT, EnvelopeStatus.IN_PROGRESS]],
			"expires_on": ["<", now_datetime()],
		},
		pluck="name",
	)
	for name in due:
		try:
			EnvelopeService(name).expire()
		except Exception as exc:  # pragma: no cover
			frappe.log_error(
				title="Nesscale Sign: expiration failed",
				message=f"Failed to expire envelope {name}: {exc}\n\n{frappe.get_traceback()}",
			)


def expire_sessions():
	"""Close out signing sessions whose envelope has expired or completed."""
	stale = frappe.get_all(
		"NS Signing Session",
		filters={"status": "Active", "expires_on": ["<", now_datetime()]},
		pluck="name",
	)
	for name in stale:
		frappe.db.set_value("NS Signing Session", name, "status", "Expired", update_modified=False)
