# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Audit logging service.

Writes append-only, hash-chained ``NS Audit Log`` rows. Request metadata (IP,
user agent, browser, OS, country) is captured automatically when a web request
is in scope and can be overridden by callers (e.g. background jobs).
"""

import frappe

from nesscale_sign.utils import request_meta


class AuditService:
	def __init__(self, envelope: str):
		self.envelope = envelope

	def log(
		self,
		action: str,
		*,
		signer_email: str | None = None,
		signer_name: str | None = None,
		details: str | None = None,
		meta: dict | None = None,
	) -> str:
		data = request_meta.collect()
		if meta:
			data.update({k: v for k, v in meta.items() if v is not None})

		doc = frappe.get_doc(
			{
				"doctype": "NS Audit Log",
				"envelope": self.envelope,
				"action": action,
				"signer_email": signer_email,
				"signer_name": signer_name,
				"details": details,
				"ip_address": data.get("ip_address"),
				"user_agent": data.get("user_agent"),
				"browser": data.get("browser"),
				"os": data.get("os"),
				"country": data.get("country"),
			}
		)
		doc.flags.ignore_permissions = True
		doc.insert(ignore_permissions=True)
		return doc.name

	def list(self, limit: int = 200) -> list[dict]:
		return frappe.get_all(
			"NS Audit Log",
			filters={"envelope": self.envelope},
			fields=[
				"name", "action", "signer_email", "signer_name", "timestamp",
				"ip_address", "browser", "os", "country", "details",
			],
			order_by="creation asc",
			limit=limit,
		)

	def verify(self) -> dict:
		from nesscale_sign.nesscale_digital_signature.doctype.ns_audit_log.ns_audit_log import (
			verify_chain,
		)

		return verify_chain(self.envelope)
