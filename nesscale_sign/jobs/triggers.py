# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Date-based auto-creation (Days Before / Days After a document date field)."""

import frappe
from frappe.utils import add_to_date, cint, nowdate

from nesscale_sign.services.integration_service import IntegrationService


def trigger_date_based():
	templates = frappe.get_all(
		"NS Template",
		filters={
			"auto_create": 1,
			"status": "Active",
			"trigger_event": ["in", ["Days Before", "Days After"]],
		},
		fields=["name", "trigger_doctype", "trigger_event", "trigger_date_field", "trigger_days"],
	)
	for t in templates:
		try:
			_process(t)
		except Exception as exc:  # pragma: no cover
			frappe.log_error(
				title="Nesscale Sign: date trigger failed",
				message=f"Trigger '{t.name}' failed: {exc}\n\n{frappe.get_traceback()}",
			)


def _process(t):
	doctype, date_field = t.get("trigger_doctype"), t.get("trigger_date_field")
	if not (doctype and date_field) or not frappe.db.has_column(doctype, date_field):
		return

	days = cint(t.get("trigger_days"))
	diff = days if t.get("trigger_event") == "Days Before" else -days
	target = add_to_date(nowdate(), days=diff)

	fieldtype = frappe.get_meta(doctype).get_field(date_field).fieldtype
	if fieldtype == "Date":
		filters = {date_field: target}
	else:
		filters = {date_field: ["between", [f"{target} 00:00:00", f"{target} 23:59:59"]]}

	for name in frappe.get_all(doctype, filters=filters, pluck="name"):
		IntegrationService._fire_template(t["name"], frappe.get_doc(doctype, name))
