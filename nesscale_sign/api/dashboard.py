# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Dashboard / analytics API endpoints."""

import frappe
from frappe.utils import add_to_date, now_datetime

from nesscale_sign.utils.constants import EnvelopeStatus


@frappe.whitelist()
def get_stats():
	statuses = [
		EnvelopeStatus.DRAFT,
		EnvelopeStatus.SENT,
		EnvelopeStatus.IN_PROGRESS,
		EnvelopeStatus.COMPLETED,
		EnvelopeStatus.DECLINED,
		EnvelopeStatus.VOIDED,
		EnvelopeStatus.EXPIRED,
	]
	# Permission-aware: get_list applies the NS Envelope query conditions, so
	# counts reflect only the envelopes this user is allowed to see (managers
	# see all; regular users see owned/sent/where-they-are-a-signer).
	counts = {s: 0 for s in statuses}
	for row in frappe.get_list("NS Envelope", fields=["status"], limit_page_length=0):
		if row.status in counts:
			counts[row.status] += 1
	total = sum(counts.values())
	completed = counts[EnvelopeStatus.COMPLETED]
	in_flight = counts[EnvelopeStatus.SENT] + counts[EnvelopeStatus.IN_PROGRESS]

	# Action-required: envelopes where the current user is an outstanding signer
	# (scoped to the user's own signer rows — they always have access to these).
	user_email = frappe.session.user
	awaiting = frappe.db.sql(
		"""
		SELECT COUNT(DISTINCT es.parent)
		FROM `tabNS Envelope Signer` es
		INNER JOIN `tabNS Envelope` e ON e.name = es.parent
		WHERE es.signer_email = %s AND es.status IN ('Sent','Viewed')
			AND e.status IN ('Sent','In Progress')
		""",
		(user_email,),
	)[0][0]

	templates = len(
		frappe.get_list(
			"NS Template",
			filters={"status": "Active"},
			fields=["name"],
			limit_page_length=0,
		)
	)
	return {
		"counts": counts,
		"total": total,
		"completed": completed,
		"in_flight": in_flight,
		"awaiting_me": awaiting,
		"completion_rate": round((completed / total) * 100, 1) if total else 0,
		"templates": templates,
	}


@frappe.whitelist()
def recent_activity(limit: int = 10):
	return frappe.get_list(
		"NS Envelope",
		fields=["name", "title", "status", "progress", "sender_name", "sent_on", "completed_on", "modified"],
		order_by="modified desc",
		page_length=int(limit),
	)


@frappe.whitelist()
def throughput(days: int = 30):
	"""Daily completed-envelope counts for the last N days (permission-aware)."""
	since = add_to_date(now_datetime(), days=-int(days))
	rows = frappe.get_list(
		"NS Envelope",
		filters={"status": "Completed", "completed_on": [">=", since]},
		fields=["completed_on"],
		limit_page_length=0,
	)
	buckets: dict[str, int] = {}
	for r in rows:
		if r.completed_on:
			day = str(r.completed_on)[:10]
			buckets[day] = buckets.get(day, 0) + 1
	return [{"day": day, "count": count} for day, count in sorted(buckets.items())]
