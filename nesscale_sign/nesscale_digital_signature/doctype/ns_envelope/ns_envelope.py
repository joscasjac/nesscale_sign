# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document


class NSEnvelope(Document):
	"""An instance of a document sent out for signing.

	Heavy lifecycle logic (send, sign, decline, void, expire) lives in the
	service layer (``services/envelope_service.py`` and ``workflow_service.py``).
	The controller only enforces invariants and keeps derived fields coherent.
	"""

	def before_insert(self):
		if not self.sender:
			self.sender = frappe.session.user
		if not self.sender_email and self.sender:
			self.sender_email = frappe.db.get_value("User", self.sender, "email") or self.sender
		if not self.sender_name and self.sender:
			self.sender_name = frappe.db.get_value("User", self.sender, "full_name") or self.sender_email

	def validate(self):
		self._assign_signer_colors()
		self._validate_signing_order()
		self.recompute_progress()

	def _assign_signer_colors(self):
		palette = [
			"#2563EB", "#DC2626", "#059669", "#D97706", "#7C3AED",
			"#DB2777", "#0891B2", "#65A30D", "#EA580C", "#4F46E5",
		]
		for idx, signer in enumerate(self.signers or []):
			if not signer.color:
				signer.color = palette[idx % len(palette)]

	def _validate_signing_order(self):
		if self.routing_type == "Parallel":
			for signer in self.signers or []:
				signer.signing_order = 1
		else:
			for signer in self.signers or []:
				if not signer.signing_order:
					signer.signing_order = 1

	def recompute_progress(self):
		signers = self.signers or []
		if not signers:
			self.progress = 0
			return
		signed = len([s for s in signers if s.status == "Signed"])
		self.progress = round((signed / len(signers)) * 100, 2)

	def add_audit(self, action: str, **kwargs):
		from nesscale_sign.services.audit_service import AuditService

		AuditService(self.name).log(action, **kwargs)

	def get_signer(self, email: str):
		for signer in self.signers or []:
			if (signer.signer_email or "").lower() == (email or "").lower():
				return signer
		return None

	def get_signer_by_token(self, token: str):
		for signer in self.signers or []:
			if signer.token == token:
				return signer
		return None
