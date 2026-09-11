# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Signing workflow engine.

Determines, for a given envelope, which signers may act right now and how the
envelope advances as signers complete. Supports both **sequential** (ordered)
and **parallel** routing. The engine mutates the in-memory envelope document;
the caller is responsible for persisting and dispatching notifications.
"""

import frappe
from frappe.utils import now_datetime

from nesscale_sign.utils.constants import EnvelopeStatus, RoutingType, SignerStatus


class WorkflowService:
	def __init__(self, envelope: "frappe.Document"):
		self.envelope = envelope

	# --------------------------------------------------------------- ordering
	@property
	def is_sequential(self) -> bool:
		return self.envelope.routing_type == RoutingType.SEQUENTIAL

	def _unfinished(self) -> list:
		return [
			s for s in self.envelope.signers if s.status not in (SignerStatus.SIGNED, SignerStatus.DECLINED)
		]

	def current_order(self) -> int | None:
		"""Lowest signing order that still has unfinished signers."""
		pending_orders = sorted({int(s.signing_order or 1) for s in self._unfinished()})
		return pending_orders[0] if pending_orders else None

	def active_signers(self) -> list:
		"""Signers permitted to act right now."""
		if self.envelope.status not in (EnvelopeStatus.SENT, EnvelopeStatus.IN_PROGRESS):
			return []
		if not self.is_sequential:
			return self._unfinished()
		order = self.current_order()
		if order is None:
			return []
		return [s for s in self._unfinished() if int(s.signing_order or 1) == order]

	def can_sign(self, signer) -> bool:
		return any(s.name == signer.name for s in self.active_signers())

	# --------------------------------------------------------------- mutations
	def signers_to_activate_on_send(self) -> list:
		"""Signers that should receive the first invitation when the envelope is sent."""
		if not self.is_sequential:
			return list(self.envelope.signers)
		order = self.current_order()
		return [s for s in self.envelope.signers if int(s.signing_order or 1) == order]

	def mark_sent(self, signers: list):
		stamp = now_datetime()
		for s in signers:
			if s.status == SignerStatus.PENDING:
				s.status = SignerStatus.SENT
				s.sent_on = stamp

	def handle_signed(self, signer) -> dict:
		"""Apply a signature; return {completed, declined, next_signers}."""
		signer.status = SignerStatus.SIGNED
		signer.signed_on = now_datetime()
		self.envelope.recompute_progress()

		if self._all_signed():
			return {"completed": True, "declined": False, "next_signers": []}

		next_signers = []
		if self.is_sequential:
			# Activate the next order only once the current order is fully signed.
			next_signers = self._maybe_activate_next_order()

		self.envelope.status = EnvelopeStatus.IN_PROGRESS
		return {"completed": False, "declined": False, "next_signers": next_signers}

	def handle_declined(self, signer, reason: str | None = None) -> dict:
		signer.status = SignerStatus.DECLINED
		signer.declined_on = now_datetime()
		signer.decline_reason = reason
		self.envelope.status = EnvelopeStatus.DECLINED
		self.envelope.declined_on = now_datetime()
		self.envelope.decline_reason = reason
		return {"completed": False, "declined": True, "next_signers": []}

	def _all_signed(self) -> bool:
		return all(s.status == SignerStatus.SIGNED for s in self.envelope.signers)

	def _maybe_activate_next_order(self) -> list:
		order = self.current_order()
		if order is None:
			return []
		self.envelope.current_order = order
		to_activate = [
			s
			for s in self.envelope.signers
			if int(s.signing_order or 1) == order and s.status == SignerStatus.PENDING
		]
		self.mark_sent(to_activate)
		return to_activate
