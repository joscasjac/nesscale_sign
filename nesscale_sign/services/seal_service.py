"""Optional PAdES service seal. Never silently downgrade a configured seal."""

import io

import frappe


def seal_pdf(content):
	key_file = frappe.conf.get("esign_pkcs12_path")
	if not key_file:
		if frappe.conf.get("esign_require_seal"):
			frappe.throw("PDF sealing is required but no certificate is configured.")
		return content, "Not configured"
	from pyhanko.pdf_utils.incremental_writer import IncrementalPdfFileWriter
	from pyhanko.sign import fields, signers
	from pyhanko.sign.timestamps import HTTPTimeStamper

	password = (frappe.conf.get("esign_pkcs12_password") or "").encode()
	signer = signers.SimpleSigner.load_pkcs12(key_file, passphrase=password)
	if signer is None:
		frappe.throw("The signing certificate could not be loaded.")
	tsa = frappe.conf.get("esign_timestamp_url")
	metadata = signers.PdfSignatureMetadata(
		field_name="OpenESignSeal", subfilter=fields.SigSeedSubFilter.PADES
	)
	output = io.BytesIO()
	signers.PdfSigner(metadata, signer=signer, timestamper=HTTPTimeStamper(tsa) if tsa else None).sign_pdf(
		IncrementalPdfFileWriter(io.BytesIO(content)), output=output
	)
	return output.getvalue(), "Sealed"
