"""Repair server-owned tokens lost to field permissions before the send fix."""

import frappe


def execute():
	for name in frappe.get_all(
		"NS Envelope", filters={"status": ["in", ["Sent", "In Progress"]]}, pluck="name"
	):
		env = frappe.get_doc("NS Envelope", name)
		for signer in env.signers:
			if not signer.token:
				signer.db_set("token", frappe.generate_hash(length=40), update_modified=False)
