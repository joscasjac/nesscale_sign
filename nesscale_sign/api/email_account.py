# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Email Account setup API (provider-based), mirroring Frappe CRM.

Lets a manager connect an outgoing (and optionally incoming) email account for
sending signing invitations, reminders and completion notices. Supported
providers preset the IMAP/SMTP hosts; a Custom option exposes the raw fields.
"""

import frappe

from nesscale_sign.api import load, require_manager

# Per-service IMAP/SMTP presets (same shape as Frappe CRM).
EMAIL_SERVICE_CONFIG = {
	"Frappe Mail": {
		"use_imap": 0,
		"use_ssl": 0,
		"validate_ssl_certificate": 0,
		"use_starttls": 0,
		"email_server": None,
		"incoming_port": 0,
		"always_use_account_email_id_as_sender": 1,
		"use_tls": 0,
		"use_ssl_for_outgoing": 0,
		"smtp_server": None,
		"smtp_port": None,
		"no_smtp_authentication": 0,
	},
	"GMail": {"email_server": "imap.gmail.com", "use_ssl": 1, "smtp_server": "smtp.gmail.com"},
	"Outlook": {
		"email_server": "imap-mail.outlook.com",
		"use_ssl": 1,
		"smtp_server": "smtp-mail.outlook.com",
	},
	"Sendgrid": {"smtp_server": "smtp.sendgrid.net", "smtp_port": 587},
	"SparkPost": {"smtp_server": "smtp.sparkpostmail.com"},
	"Yahoo": {
		"email_server": "imap.mail.yahoo.com",
		"use_ssl": 1,
		"smtp_server": "smtp.mail.yahoo.com",
		"smtp_port": 587,
	},
	"Yandex": {
		"email_server": "imap.yandex.com",
		"use_ssl": 1,
		"smtp_server": "smtp.yandex.com",
		"smtp_port": 587,
	},
	"Custom": {},
}

SERVICES = [
	{
		"name": "GMail",
		"custom": False,
		"info": "Requires 2FA and an app-specific password.",
		"link": "https://support.google.com/accounts/answer/185833",
	},
	{
		"name": "Outlook",
		"custom": False,
		"info": "Requires 2FA and an app-specific password.",
		"link": "https://support.microsoft.com/en-us/account-billing/how-to-get-and-use-app-passwords-5896ed9b-4263-e681-128a-a6f2979a7944",
	},
	{
		"name": "Sendgrid",
		"custom": False,
		"info": "Use an API key as the SMTP password.",
		"link": "https://sendgrid.com/docs/",
	},
	{
		"name": "SparkPost",
		"custom": False,
		"info": "Use your SparkPost SMTP credentials.",
		"link": "https://support.sparkpost.com/",
	},
	{
		"name": "Yahoo",
		"custom": False,
		"info": "Requires 2FA and an app-specific password.",
		"link": "https://help.yahoo.com/kb/SLN15241.html",
	},
	{
		"name": "Yandex",
		"custom": False,
		"info": "Requires 2FA and an app-specific password.",
		"link": "https://yandex.com/support/id/authorization/app-passwords.html",
	},
	{
		"name": "Frappe Mail",
		"custom": True,
		"info": "Requires an API key & secret from your Frappe Mail account.",
		"link": "https://github.com/frappe/mail",
	},
	{"name": "Custom", "custom": True, "info": "Enter your own IMAP/SMTP server details.", "link": ""},
]


@frappe.whitelist()
def email_services():
	return SERVICES


@frappe.whitelist()
def list_email_accounts():
	require_manager()
	return frappe.get_list(
		"Email Account",
		fields=[
			"name",
			"email_account_name",
			"email_id",
			"service",
			"enable_incoming",
			"enable_outgoing",
			"default_incoming",
			"default_outgoing",
		],
		order_by="creation desc",
		limit_page_length=0,
	)


@frappe.whitelist()
def create_email_account(data: dict | None = None):
	require_manager()
	data = load(data) or {}
	service = data.get("service")
	service_config = EMAIL_SERVICE_CONFIG.get(service)
	if service_config is None:
		frappe.throw(frappe._("Service '{0}' is not supported").format(service))

	doc = frappe.get_doc(
		{
			"doctype": "Email Account",
			"email_id": data.get("email_id"),
			"email_account_name": data.get("email_account_name"),
			"service": service,
			"enable_incoming": 1 if data.get("enable_incoming") else 0,
			"enable_outgoing": 1 if data.get("enable_outgoing", True) else 0,
			"default_incoming": 1 if data.get("default_incoming") else 0,
			"default_outgoing": 1 if data.get("default_outgoing", True) else 0,
			"smtp_port": data.get("smtp_port") or 587,
			"use_tls": 1,
			**service_config,
		}
	)

	if service == "Frappe Mail":
		doc.api_key = data.get("api_key")
		doc.api_secret = data.get("api_secret")
		doc.frappe_mail_site = data.get("frappe_mail_site")
	elif service == "Custom":
		doc.smtp_server = data.get("smtp_server")
		doc.smtp_port = data.get("smtp_port") or 587
		doc.email_server = data.get("email_server")
		doc.use_imap = 1 if data.get("use_imap") else 0
		doc.use_ssl = 1 if data.get("use_ssl") else 0
		doc.password = data.get("password")
	else:
		doc.password = data.get("password")

	try:
		if doc.enable_incoming and service not in ("Frappe Mail",):
			# Validate incoming credentials before saving (CRM behaviour).
			doc.get_incoming_server()
		doc.save(ignore_permissions=True)
	except Exception as exc:
		frappe.throw(str(exc))

	return {"name": doc.name}


@frappe.whitelist()
def update_email_account(name: str, data=None):
	require_manager()
	data = load(data) or {}
	doc = frappe.get_doc("Email Account", name)
	for field in (
		"email_account_name",
		"enable_incoming",
		"enable_outgoing",
		"default_incoming",
		"default_outgoing",
	):
		if field in data:
			doc.set(
				field,
				1
				if data[field] in (1, True, "1")
				else 0
				if field.startswith(("enable", "default"))
				else data[field],
			)
	if data.get("password"):
		doc.password = data["password"]
	doc.save(ignore_permissions=True)
	return {"name": doc.name}


@frappe.whitelist()
def delete_email_account(name: str):
	require_manager()
	frappe.delete_doc("Email Account", name, ignore_permissions=True)
	return {"deleted": True}
