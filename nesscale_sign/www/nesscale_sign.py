# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""SPA bootstrap controller.

Serves the single-page app. The public signing routes (``/sign/<token>``) are
guest-accessible; every other route requires an authenticated session and is
redirected to login otherwise. Sensitive data is never embedded here — it is
fetched at runtime through permission-checked / token-checked API methods.
"""

import frappe
from frappe.utils import cint, get_system_timezone

no_cache = 1


def get_context(context):
	path = frappe.local.request.path if getattr(frappe.local, "request", None) else ""
	is_public = path.startswith("/sign")

	if not is_public and frappe.session.user == "Guest":
		frappe.local.flags.redirect_location = f"/login?redirect-to={path}"
		raise frappe.Redirect

	context.boot = get_boot()
	context.no_cache = 1
	return context


def get_boot():
	return frappe._dict(
		{
			"frappe_version": frappe.__version__,
			"app_version": frappe.get_attr("nesscale_sign.__version__"),
			"default_route": "/nesscale-sign",
			"site_name": frappe.local.site,
			"read_only_mode": frappe.flags.read_only,
			"csrf_token": frappe.sessions.get_csrf_token(),
			"setup_complete": cint(frappe.get_system_settings("setup_complete")),
			"user": frappe.session.user,
			"timezone": {
				"system": get_system_timezone(),
				"user": frappe.db.get_value("User", frappe.session.user, "time_zone")
				or get_system_timezone(),
			},
		}
	)
