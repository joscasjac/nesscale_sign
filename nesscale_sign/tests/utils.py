# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Shared helpers for the Nesscale Sign test suite."""

import base64
import io

import fitz
import frappe

from nesscale_sign.services.envelope_service import EnvelopeService
from nesscale_sign.services.template_service import TemplateService
from nesscale_sign.utils import files


def make_pdf(pages: int = 2) -> bytes:
	doc = fitz.open()
	for i in range(pages):
		doc.new_page(width=595, height=842).insert_text((72, 72), f"Test page {i + 1}")
	data = doc.tobytes()
	doc.close()
	return data


def make_private_pdf(name: str = "test.pdf", pages: int = 2) -> str:
	f = files.save_private_file(name, make_pdf(pages))
	return f.file_url


def make_template(title="Test Template", roles=None, fields=None, publish=True):
	roles = roles or [{"role_label": "Signer", "role_key": "signer", "signing_order": 1}]
	tmpl = TemplateService.create(
		{"title": title, "pdf_file": make_private_pdf(f"{title}.pdf"), "signer_roles": roles}
	)
	if fields is None:
		fields = [
			{
				"field_type": "Text", "label": "Full Name", "signer_role": "signer",
				"page": 1, "pos_x": 0.1, "pos_y": 0.3, "width": 0.3, "height": 0.04, "required": 1,
			},
			{
				"field_type": "Signature", "label": "Sign", "signer_role": "signer",
				"page": 1, "pos_x": 0.1, "pos_y": 0.6, "width": 0.2, "height": 0.06, "required": 1,
			},
		]
	TemplateService(tmpl.name).save_fields(fields)
	if publish:
		TemplateService(tmpl.name).publish()
	return frappe.get_doc("NS Template", tmpl.name)


def make_envelope(template, signers, routing="Sequential", send=True):
	env = EnvelopeService.create_from_template(
		template, {"title": "Test Envelope", "routing_type": routing, "signers": signers}
	)
	if send:
		EnvelopeService(env.name).send()
	return frappe.get_doc("NS Envelope", env.name)


def two_signers_single():
	"""A single-signer list bound to the default 'signer' role."""
	return [{"signer_name": "Solo", "signer_email": "solo@test.com", "role_key": "signer", "signing_order": 1}]


def signature_payload():
	from PIL import Image

	img = Image.new("RGBA", (300, 100), (255, 255, 255, 0))
	buf = io.BytesIO()
	img.save(buf, "PNG")
	return {
		"type": "Draw",
		"image": "data:image/png;base64," + base64.b64encode(buf.getvalue()).decode(),
	}
