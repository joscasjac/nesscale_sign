# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""DocType auto-creation + reversal.

When a reference document fires a configured event (New / Save / Submit /
Cancel / Value Change / date-based), an envelope is created from the template,
with signer details and fields resolved from that document. When the reference
document is **cancelled or deleted**, any still-open envelopes created from it
are voided (reversed).
"""

import json

import frappe

# Frappe document lifecycle hook -> the event label stored on the template.
EVENT_LABELS = {
	"after_insert": "New",
	"on_update": "Save",
	"on_submit": "Submit",
	"on_cancel": "Cancel",
}

_TRIGGER_CACHE_KEY = "ns_sign_trigger_doctypes"
_OPEN_STATUSES = ("Draft", "Sent", "In Progress")


def get_trigger_doctypes() -> set[str]:
	"""Cached set of reference DocTypes with at least one active auto-create template."""

	def _build():
		rows = frappe.get_all(
			"NS Template",
			filters={"auto_create": 1, "status": "Active"},
			pluck="trigger_doctype",
		)
		return [r for r in rows if r]

	return set(frappe.cache().get_value(_TRIGGER_CACHE_KEY, _build) or [])


def clear_trigger_cache():
	frappe.cache().delete_value(_TRIGGER_CACHE_KEY)


def on_doc_event(doc, method=None):
	"""Universal ``doc_events`` entry point (registered for ``*``)."""
	try:
		IntegrationService.handle_doc_event(doc, method)
	except Exception as exc:  # never break the host document's transaction
		frappe.log_error(
			title="Nesscale Sign: doc trigger failed",
			message=f"Trigger failed for {doc.doctype} {doc.name}: {exc}\n\n{frappe.get_traceback()}",
		)


class IntegrationService:
	# ----------------------------------------------------------- dispatcher
	@staticmethod
	def handle_doc_event(doc, method):
		if frappe.flags.in_install or frappe.flags.in_migrate or frappe.flags.in_patch:
			return
		if (doc.doctype or "").startswith("NS "):
			return

		# Reversal: void open envelopes when the source is cancelled or deleted.
		if method in ("on_cancel", "on_trash"):
			IntegrationService._reverse_envelopes(doc, method)

		# Creation.
		if doc.doctype not in get_trigger_doctypes():
			return
		events = []
		label = EVENT_LABELS.get(method)
		if label:
			events.append(label)
		if method == "on_update":
			events.append("Value Change")
		if not events:
			return

		templates = frappe.get_all(
			"NS Template",
			filters={
				"auto_create": 1,
				"status": "Active",
				"trigger_doctype": doc.doctype,
				"trigger_event": ["in", events],
			},
			fields=["name", "trigger_event", "trigger_value_field", "trigger_value_to"],
		)
		for t in templates:
			if t.trigger_event == "Value Change" and not IntegrationService._value_changed(doc, t):
				continue
			IntegrationService._fire_template(t.name, doc)

	# ----------------------------------------------------------- reversal
	@staticmethod
	def _reverse_envelopes(doc, method):
		from nesscale_sign.services.envelope_service import EnvelopeService

		like = f'%"ref_name": "{doc.name}"%'
		rows = frappe.get_all(
			"NS Envelope",
			filters={"metadata_json": ["like", like], "status": ["in", _OPEN_STATUSES]},
			fields=["name", "metadata_json"],
		)
		verb = "deleted" if method == "on_trash" else "cancelled"
		for row in rows:
			try:
				meta = json.loads(row.metadata_json or "{}")
			except (ValueError, TypeError):
				continue
			if meta.get("ref_doctype") == doc.doctype and meta.get("ref_name") == doc.name:
				EnvelopeService(row.name).void(f"Reference {doc.doctype} {doc.name} was {verb}")

	# ----------------------------------------------------------- creation
	@staticmethod
	def _value_changed(doc, template) -> bool:
		field = template.get("trigger_value_field")
		if not field or doc.is_new():
			return False
		before = doc.get_doc_before_save()
		old = before.get(field) if before else None
		new = doc.get(field)
		if old == new:
			return False
		target = template.get("trigger_value_to")
		if target not in (None, "") and str(new) != str(target):
			return False
		return True

	@staticmethod
	def _fire_template(template: str, doc):
		from nesscale_sign.services.envelope_service import EnvelopeService

		# Idempotency: one envelope per (template, reference document).
		if frappe.db.exists(
			"NS Envelope",
			{"template": template, "metadata_json": ["like", f'%"ref_name": "{doc.name}"%']},
		):
			return

		tmpl = frappe.get_doc("NS Template", template)
		signers = IntegrationService._signers_from_document(tmpl, doc)
		env = EnvelopeService.create_from_template(
			template,
			{
				"title": f"{tmpl.title} — {doc.name}",
				"signers": signers,
				"source_doctype": doc.doctype,
				"source_name": doc.name,
			},
		)
		# Auto-send only when every signer is fully resolved (name + email).
		all_complete = bool(signers) and all(
			s.get("signer_email") and s.get("signer_name") for s in signers
		)
		if tmpl.trigger_auto_send and all_complete:
			EnvelopeService(env.name).send()

	@staticmethod
	def _signers_from_document(tmpl, doc) -> list[dict]:
		"""Resolve each role's name/email from a document field OR a manual value
		(field wins when set). Blank values yield a Draft the user completes."""
		from frappe.utils import validate_email_address

		def resolve(field, manual):
			value = doc.get(field) if field else None
			if value in (None, ""):
				value = manual
			return (value or "").strip() if isinstance(value, str) else (value or "")

		signers = []
		for role in tmpl.signer_roles:
			raw_email = resolve(role.source_email_field, role.get("manual_email"))
			email = validate_email_address(raw_email) if raw_email else ""
			name = resolve(role.source_name_field, role.get("manual_name")) or email
			signers.append(
				{
					"signer_name": name,
					"signer_email": email or "",
					"role_key": role.role_key,
					"role_label": role.role_label,
					"signing_order": role.signing_order,
				}
			)
		return signers
