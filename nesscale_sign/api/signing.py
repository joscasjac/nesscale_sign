# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Public signing API — guest accessible, authenticated solely by secure token.

No Frappe login is required. The 40-char token issued per signer is the only
credential; all access is scoped to the envelope and signer that token resolves
to. Files are streamed through these endpoints rather than via public URLs.
"""

import frappe
from frappe.rate_limiter import rate_limit

from nesscale_sign.api import load
from nesscale_sign.services.signing_service import SigningService

# NOTE: Every endpoint in this module is intentionally guest-accessible. The sole
# credential is the 40-char per-signer token; SigningService._resolve raises
# PermissionError for any unknown/expired token before any data is touched, and
# all access is scoped to the envelope+signer that token resolves to. The
# nosemgrep markers below acknowledge `guest-whitelisted-method` by design.


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=120, seconds=60)  # nosemgrep: guest-whitelisted-method — token-authenticated
def get_context(token: str):
	return SigningService(token).get_context()


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=120, seconds=60)  # nosemgrep: guest-whitelisted-method — token-authenticated
def get_pdf(token: str):
	svc = SigningService(token)
	content = svc.get_pdf_bytes()
	frappe.local.response.filename = f"{svc.envelope.name}.pdf"
	frappe.local.response.filecontent = content
	frappe.local.response.type = "pdf"
	frappe.local.response.display_content_as = "inline"


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=60)  # nosemgrep: guest-whitelisted-method — token-authenticated
def save_progress(token: str, values: dict | str | None = None):
	return SigningService(token).save_values(load(values) or {})


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=60)  # nosemgrep: guest-whitelisted-method — token-authenticated
def submit(
	token: str, values: dict | str | None = None, signature: dict | str | None = None, consent: bool = False
):
	return SigningService(token).submit(
		load(values) or {}, load(signature) or {}, consent=consent is True or consent == "true"
	)


@frappe.whitelist(allow_guest=True, methods=["POST"])
@rate_limit(limit=30, seconds=60)  # nosemgrep: guest-whitelisted-method — token-authenticated
def decline(token: str, reason: str | None = None):
	return SigningService(token).decline(reason)


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=120, seconds=60)  # nosemgrep: guest-whitelisted-method — token-authenticated
def download_completed(token: str):
	"""Allow a signer to download the final document once the envelope completes."""
	svc = SigningService(token)
	if svc.envelope.status != "Completed" or not svc.envelope.signed_pdf:
		frappe.throw(frappe._("The completed document is not available."))
	from nesscale_sign.services.audit_service import AuditService
	from nesscale_sign.utils import files

	AuditService(svc.envelope.name).log(
		"Downloaded", signer_email=svc.signer.signer_email, details="Signer downloaded final PDF"
	)
	frappe.local.response.filename = f"{svc.envelope.name}-signed.pdf"
	frappe.local.response.filecontent = files.read_file_content(svc.envelope.signed_pdf)
	frappe.local.response.type = "pdf"
	frappe.local.response.display_content_as = "attachment"


@frappe.whitelist(allow_guest=True)
@rate_limit(limit=120, seconds=60)  # nosemgrep: guest-whitelisted-method — token-authenticated
def download_certificate(token: str):
	"""The same signer token grants access to its completed evidence record."""
	svc = SigningService(token)
	if svc.envelope.status != "Completed" or not svc.envelope.certificate_pdf:
		frappe.throw(frappe._("The completion certificate is not available."))
	from nesscale_sign.utils import files

	frappe.local.response.filename = f"{svc.envelope.name}-certificate.pdf"
	frappe.local.response.filecontent = files.read_file_content(svc.envelope.certificate_pdf)
	frappe.local.response.type = "pdf"
	frappe.local.response.display_content_as = "attachment"
