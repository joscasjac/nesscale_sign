# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Seed editable Frappe ``Email Template`` records.

The wording is deliberately simple and generic (no sender name, no per-send
message). Administrators can customise it from Desk; the records are created
only if missing so edits are never overwritten.
"""

import frappe

# notification_type -> Email Template name
TEMPLATE_NAMES = {
	"Invitation": "Nesscale Sign Invitation",
	"Reminder": "Nesscale Sign Reminder",
	"Completed": "Nesscale Sign Completed",
	"Declined": "Nesscale Sign Declined",
	"Expired": "Nesscale Sign Expired",
	"Voided": "Nesscale Sign Voided",
}

_OPEN = """
<div style="font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;
	max-width:520px;margin:0 auto;color:#1f2937;">
	<div style="padding:20px 0 16px;border-bottom:1px solid #e5e7eb;">
		<span style="font-size:17px;font-weight:700;color:#2563eb;">{{ brand }}</span>
	</div>
	<div style="padding:24px 0;font-size:14px;line-height:1.65;">
"""

_CLOSE = """
	</div>
	<div style="padding:16px 0;border-top:1px solid #e5e7eb;font-size:12px;color:#9ca3af;">
		This is an automated message from {{ brand }}.
	</div>
</div>
"""


def _button(url, label):
	return (
		f'<a href="{{{{ {url} }}}}" style="display:inline-block;background:#2563eb;color:#ffffff;'
		"text-decoration:none;padding:11px 22px;border-radius:8px;font-weight:600;"
		f'font-size:14px;margin:18px 0;">{label}</a>'
	)


_INVITATION = (
	_OPEN
	+ """
	<p>Hi {{ signer_name }},</p>
	<p>You have a document waiting for your signature:
	<b>{{ title }}</b>{% if role %} (as {{ role }}){% endif %}.</p>
"""
	+ _button("sign_url", "Review &amp; Sign")
	+ """
	{% if expires_on %}<p style="color:#6b7280;">Please sign before {{ expires_on }}.</p>{% endif %}
	<p style="color:#9ca3af;font-size:12px;">If the button doesn't work, copy this link:<br>
		<a href="{{ sign_url }}" style="color:#2563eb;">{{ sign_url }}</a></p>
"""
	+ _CLOSE
)

_REMINDER = (
	_OPEN
	+ """
	<p>Hi {{ signer_name }},</p>
	<p>A quick reminder that <b>{{ title }}</b> is still waiting for your signature.</p>
"""
	+ _button("sign_url", "Sign Now")
	+ """
	{% if expires_on %}<p style="color:#6b7280;">Please sign before {{ expires_on }}.</p>{% endif %}
"""
	+ _CLOSE
)

_COMPLETED = (
	_OPEN
	+ """
	<p><b>{{ title }}</b> has been signed by everyone. A copy is kept on file.</p>
"""
	+ _CLOSE
)

_DECLINED = (
	_OPEN
	+ """
	<p><b>{{ title }}</b> was declined{% if reason %}: {{ reason }}{% endif %}.</p>
	<p style="color:#6b7280;">No further action is required.</p>
"""
	+ _CLOSE
)

_EXPIRED = (
	_OPEN
	+ """
	<p><b>{{ title }}</b> has expired and can no longer be signed.</p>
"""
	+ _CLOSE
)

_VOIDED = (
	_OPEN
	+ """
	<p><b>{{ title }}</b> has been voided{% if reason %}: {{ reason }}{% endif %}.</p>
	<p style="color:#6b7280;">No further action is required.</p>
"""
	+ _CLOSE
)

_DEFINITIONS = [
	{
		"name": "Nesscale Sign Invitation",
		"subject": "Signature requested: {{ title }}",
		"response": _INVITATION,
	},
	{"name": "Nesscale Sign Reminder", "subject": "Reminder: please sign {{ title }}", "response": _REMINDER},
	{"name": "Nesscale Sign Completed", "subject": "Completed: {{ title }}", "response": _COMPLETED},
	{"name": "Nesscale Sign Declined", "subject": "Declined: {{ title }}", "response": _DECLINED},
	{"name": "Nesscale Sign Expired", "subject": "Expired: {{ title }}", "response": _EXPIRED},
	{"name": "Nesscale Sign Voided", "subject": "Voided: {{ title }}", "response": _VOIDED},
]


def seed_email_templates():
	for definition in _DEFINITIONS:
		if frappe.db.exists("Email Template", definition["name"]):
			continue
		frappe.get_doc(
			{
				"doctype": "Email Template",
				"name": definition["name"],
				"subject": definition["subject"],
				"use_html": 0,
				"response": definition["response"],
			}
		).insert(ignore_permissions=True)
