"""Lifecycle-aware adapters for operations not suitable for direct forwarding."""

import json

import frappe

from nesscale_sign.api import envelope, mail
from nesscale_sign.utils.security import lock_envelope


def _locked(name, permission="write"):
	doc = frappe.get_doc("NS Envelope", name)
	doc.check_permission(permission)
	lock_envelope(name)
	doc.reload()
	return doc


def save_document_fields(name, fields):
	_locked(name)
	return envelope.save_envelope_fields(name, fields)


def delete_draft(name):
	_locked(name, "delete")
	return envelope.delete_envelope(name)


def retry_completion(name):
	doc = _locked(name)
	if (
		doc.status not in ("Sent", "In Progress")
		or not doc.signers
		or any(s.status != "Signed" for s in doc.signers)
	):
		frappe.throw(
			"Completion can only be retried for an unfinished document after all recipients have signed."
		)
	return envelope.retry_completion(name)


def my_pending_signatures():
	# Do not put bearer signing tokens into assistant logs or conversations.
	return {
		"documents": [
			{k: v for k, v in row.items() if k != "token"} for row in envelope.my_pending_signatures()
		],
		"signing_inbox_url": frappe.utils.get_url("/nesscale-sign"),
	}


def list_attachments(names):
	return mail.list_attachments(json.dumps(names))


def workflow_guide():
	from pathlib import Path

	from nesscale_sign.mcp.tools import definitions

	frappe.has_permission("NS Envelope", "read", throw=True)
	return {
		"workflow": Path(__file__)
		.with_name("skills")
		.joinpath("erpnext-signable-documents", "SKILL.md")
		.read_text(),
		"tools": [{"name": s["name"], "description": s["description"]} for s in definitions()],
	}
