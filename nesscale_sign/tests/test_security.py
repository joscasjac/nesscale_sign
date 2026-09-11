"""Regression tests for signing trust boundaries; run on an isolated Frappe site."""

import json
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase
from frappe.utils import add_days, now_datetime

from nesscale_sign.api.envelope import get_envelope
from nesscale_sign.services.audit_service import AuditService
from nesscale_sign.services.envelope_service import EnvelopeService
from nesscale_sign.services.finalization import finalize_envelope
from nesscale_sign.services.signing_service import SigningService
from nesscale_sign.tests.utils import make_envelope, make_template, signature_payload, two_signers_single
from nesscale_sign.utils import files
from nesscale_sign.utils.security import digest


class TestSigningBoundaries(FrappeTestCase):
	def setUp(self):
		frappe.set_user("Administrator")
		self.template = make_template("Security regression")
		self.envelope = make_envelope(self.template.name, two_signers_single())
		self.token = self.envelope.signers[0].token

	def test_expired_token_cannot_read_pdf_or_context(self):
		frappe.db.set_value("NS Envelope", self.envelope.name, "expires_on", add_days(now_datetime(), -1))
		with self.assertRaises(frappe.PermissionError):
			SigningService(self.token).get_pdf_bytes()
		with self.assertRaises(frappe.PermissionError):
			SigningService(self.token).get_context()

	def test_voided_token_cannot_read(self):
		EnvelopeService(self.envelope.name).void("Test cancellation")
		with self.assertRaises(frappe.PermissionError):
			SigningService(self.token).get_context()

	def test_readonly_and_signature_fields_cannot_be_filled_by_save_progress(self):
		rows = frappe.get_all(
			"NS Envelope Field",
			filters={"envelope": self.envelope.name},
			fields=["name", "field_key", "field_type"],
		)
		text = next(r for r in rows if r.field_type == "Text")
		signature = next(r for r in rows if r.field_type == "Signature")
		frappe.db.set_value("NS Envelope Field", text.name, {"read_only": 1, "value": "Protected"})
		SigningService(self.token).save_values({text.field_key: "Changed", signature.field_key: "Fake"})
		self.assertEqual(frappe.db.get_value("NS Envelope Field", text.name, "value"), "Protected")
		self.assertFalse(frappe.db.get_value("NS Envelope Field", signature.name, "filled"))

	def test_explicit_consent_required(self):
		with self.assertRaises(frappe.ValidationError):
			SigningService(self.token).submit({}, signature_payload(), consent=False)
		self.assertNotEqual(
			frappe.db.get_value("NS Envelope Signer", self.envelope.signers[0].name, "status"), "Signed"
		)

	def test_api_does_not_disclose_signing_tokens(self):
		result = get_envelope(self.envelope.name)
		self.assertNotIn(self.token, json.dumps(result, default=str))

	def test_source_snapshot_hash_and_changed_source_block_completion(self):
		self.envelope.reload()
		self.assertEqual(
			self.envelope.source_sha256, digest(files.read_file_content(self.envelope.source_pdf))
		)
		self._sign()
		frappe.db.set_value("NS Envelope", self.envelope.name, "source_sha256", "bad")
		with self.assertRaises(frappe.ValidationError):
			EnvelopeService(self.envelope.name).finalize()

	def test_completion_is_idempotent_and_certificate_contains_completion(self):
		self._sign()
		EnvelopeService(self.envelope.name).finalize()
		before = frappe.db.count("File", {"attached_to_name": self.envelope.name})
		EnvelopeService(self.envelope.name).finalize()
		self.assertEqual(before, frappe.db.count("File", {"attached_to_name": self.envelope.name}))
		env = frappe.get_doc("NS Envelope", self.envelope.name)
		self.assertEqual(env.status, "Completed")
		self.assertEqual(digest(files.read_file_content(env.signed_pdf)), env.signed_sha256)
		import fitz

		with fitz.open(stream=files.read_file_content(env.certificate_pdf), filetype="pdf") as pdf:
			text = " ".join(p.get_text() for p in pdf)
		self.assertIn("Completed", text)
		self.assertIn("All signers completed", text)

	def test_worker_failure_preserves_signatures_and_is_retryable(self):
		self._sign()
		with patch(
			"nesscale_sign.services.envelope_service.pdf_service.generate_filled_pdf",
			side_effect=RuntimeError("test error"),
		):
			finalize_envelope(self.envelope.name)
		env = frappe.get_doc("NS Envelope", self.envelope.name)
		self.assertEqual(env.finalization_status, "Failed")
		self.assertEqual(env.signers[0].status, "Signed")
		finalize_envelope(env.name)
		self.assertEqual(frappe.db.get_value("NS Envelope", env.name, "status"), "Completed")

	def test_audit_deletion_blocked(self):
		name = frappe.db.get_value("NS Audit Log", {"envelope": self.envelope.name}, "name")
		with self.assertRaises(frappe.ValidationError):
			frappe.delete_doc("NS Audit Log", name, ignore_permissions=True)

	def test_generic_document_update_cannot_change_sent_document(self):
		env = frappe.get_doc("NS Envelope", self.envelope.name)
		env.title = "Changed after sending"
		with self.assertRaises(frappe.ValidationError):
			env.save()

	def _sign(self):
		svc = SigningService(self.token)
		context = svc.get_context()
		values = {f["field_key"]: "Test signer" for f in context["fields"] if f["field_type"] == "Text"}
		result = svc.submit(values, signature_payload(), consent=True)
		self.assertEqual(result["status"], "processing")

	def test_unrelated_user_cannot_read_document_or_evidence(self):
		user = "unrelated-esign@example.test"
		if not frappe.db.exists("User", user):
			frappe.get_doc(
				{
					"doctype": "User",
					"email": user,
					"first_name": "Access test",
					"send_welcome_email": 0,
					"roles": [{"role": "Nesscale Sign User"}],
				}
			).insert(ignore_permissions=True)
		try:
			frappe.set_user(user)
			with self.assertRaises(frappe.PermissionError):
				get_envelope(self.envelope.name)
			row = frappe.db.get_value("NS Envelope Field", {"envelope": self.envelope.name}, "name")
			self.assertFalse(frappe.has_permission("NS Envelope Field", "read", doc=row))
			self.assertFalse(frappe.has_permission("NS Audit Log", "create"))
		finally:
			frappe.set_user("Administrator")

	def test_readonly_prefill_survives_materialization(self):
		template = make_template(
			"Prefill",
			fields=[
				{
					"field_type": "Text",
					"label": "Reference",
					"signer_role": "signer",
					"page": 1,
					"pos_x": 0.1,
					"pos_y": 0.1,
					"width": 0.3,
					"height": 0.05,
					"read_only": 1,
					"default_value": "PO-123",
				}
			],
		)
		env = make_envelope(template.name, two_signers_single(), send=False)
		self.assertEqual(frappe.db.get_value("NS Envelope Field", {"envelope": env.name}, "value"), "PO-123")

	def test_explicit_expiry_preserved_on_creation(self):
		expires = add_days(now_datetime(), 7)
		env = EnvelopeService.create_from_template(
			self.template.name, {"signers": two_signers_single(), "expires_on": expires}
		)
		self.assertEqual(str(env.expires_on), str(expires))
