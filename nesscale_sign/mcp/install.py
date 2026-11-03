"""Keep optional FAC metadata accurate without changing administrator access choices."""

import frappe


def sync_tool_metadata():
	if "frappe_assistant_core" not in frappe.get_installed_apps() or not frappe.db.table_exists(
		"FAC Tool Configuration"
	):
		return
	from nesscale_sign.mcp.tools import definitions

	for spec in definitions():
		name = spec["name"]
		# FAC's normal migration creates external tool rows. Do not auto-enable,
		# create role grants, or change a deliberate category override here.
		if not frappe.db.exists("FAC Tool Configuration", name):
			continue
		doc = frappe.get_doc("FAC Tool Configuration", name)
		if doc.source_app != "nesscale_sign":
			continue
		category = "read_only" if spec["annotations"]["readOnlyHint"] else "read_write"
		values = {"description": spec["description"], "auto_detected_category": category}
		if not doc.category_override:
			values["tool_category"] = category
		frappe.db.set_value("FAC Tool Configuration", name, values)
