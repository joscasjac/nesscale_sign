"""Commit signatures first, then create completion artifacts in a worker."""

import frappe

from nesscale_sign.utils.security import lock_envelope


def schedule_finalization(name):
	lock_envelope(name)
	doc = frappe.get_doc("NS Envelope", name)
	if doc.status == "Completed":
		return
	if (
		doc.status not in ("Sent", "In Progress")
		or not doc.signers
		or not all(s.status == "Signed" for s in doc.signers)
	):
		frappe.throw("Only fully signed documents can be completed.")
	frappe.db.set_value("NS Envelope", name, {"finalization_status": "Pending", "finalization_error": ""})
	frappe.enqueue(
		"nesscale_sign.services.finalization.finalize_envelope",
		name=name,
		queue="long",
		timeout=300,
		enqueue_after_commit=True,
	)


def finalize_envelope(name):
	from nesscale_sign.services.envelope_service import EnvelopeService

	frappe.db.savepoint("esign_finalize")
	try:
		EnvelopeService(name).finalize()
	except Exception:
		frappe.db.rollback(save_point="esign_finalize")
		frappe.log_error(title="Open E-Sign completion failed", message=frappe.get_traceback())
		frappe.db.set_value(
			"NS Envelope",
			name,
			{
				"finalization_status": "Failed",
				"finalization_error": "PDF processing failed. A manager can retry completion; signatures have been preserved.",
			},
		)
