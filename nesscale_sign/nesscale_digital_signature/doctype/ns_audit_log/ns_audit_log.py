# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import hashlib
import json

import frappe
from frappe import _
from frappe.model.document import Document
from frappe.utils import now_datetime


class NSAuditLog(Document):
	"""Append-only, tamper-evident audit trail.

	Each row is chained to the previous row for the same envelope via a SHA-256
	hash, so any retroactive edit breaks the chain and is detectable by
	``verify_chain``. Rows are immutable once written.
	"""

	def before_insert(self):
		from nesscale_sign.utils.security import lock_envelope

		lock_envelope(self.envelope)
		if not self.timestamp:
			self.timestamp = now_datetime()
		self.prev_hash = self._get_prev_hash()
		self.hash = self._compute_hash()

	def _get_prev_hash(self) -> str:
		if not self.envelope:
			return ""
		last = frappe.get_all(
			"NS Audit Log",
			filters={"envelope": self.envelope},
			fields=["hash"],
			order_by="creation desc",
			limit=1,
		)
		return last[0]["hash"] if last else ""

	def _payload(self) -> str:
		return json.dumps(
			{
				"envelope": self.envelope,
				"action": self.action,
				"signer_email": self.signer_email,
				"ip_address": self.ip_address,
				"timestamp": str(self.timestamp),
				"details": self.details,
				"prev_hash": self.prev_hash,
			},
			sort_keys=True,
			default=str,
		)

	def _compute_hash(self) -> str:
		return hashlib.sha256(self._payload().encode("utf-8")).hexdigest()

	def on_update(self):
		# Immutable: block edits to an already-persisted row.
		if not self.flags.in_insert and not self.flags.ignore_audit_immutability:
			frappe.throw(_("Audit Log entries are immutable and cannot be modified."))

	def on_trash(self):
		frappe.throw(_("Audit Log entries cannot be deleted."))


def verify_chain(envelope: str) -> dict:
	"""Recompute the hash chain for an envelope; report the first broken link."""
	rows = frappe.get_all(
		"NS Audit Log",
		filters={"envelope": envelope},
		fields=["name"],
		order_by="creation asc",
	)
	prev = ""
	for row in rows:
		doc = frappe.get_doc("NS Audit Log", row["name"])
		expected = doc._compute_hash()
		if doc.prev_hash != prev or doc.hash != expected:
			return {"valid": False, "broken_at": row["name"], "count": len(rows)}
		prev = doc.hash
	return {"valid": True, "broken_at": None, "count": len(rows)}
