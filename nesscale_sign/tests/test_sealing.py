"""Verify the optional service seal with a disposable local certificate."""

import io
import tempfile
from datetime import UTC, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

import frappe
from frappe.tests.utils import FrappeTestCase

from nesscale_sign.services.seal_service import seal_pdf
from nesscale_sign.tests.utils import make_pdf


class TestServiceSeal(FrappeTestCase):
	def test_unconfigured_and_required(self):
		with patch.dict(frappe.conf, {"esign_pkcs12_path": None, "esign_require_seal": False}):
			original = make_pdf()
			self.assertEqual(seal_pdf(original), (original, "Not configured"))
		with patch.dict(frappe.conf, {"esign_pkcs12_path": None, "esign_require_seal": True}):
			with self.assertRaises(frappe.ValidationError):
				seal_pdf(make_pdf())

	def test_seal_is_cryptographically_valid(self):
		try:
			from pyhanko.pdf_utils.reader import PdfFileReader
			from pyhanko.sign.validation import validate_pdf_signature
			from pyhanko_certvalidator import ValidationContext
		except ImportError:
			self.skipTest("Install the sealing extra to verify PAdES")
		from asn1crypto import x509 as asn1_x509
		from cryptography import x509
		from cryptography.hazmat.primitives import hashes, serialization
		from cryptography.hazmat.primitives.asymmetric import rsa
		from cryptography.hazmat.primitives.serialization import pkcs12
		from cryptography.x509.oid import NameOID

		key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
		name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Local test only")])
		now = datetime.now(UTC)
		cert = (
			x509.CertificateBuilder()
			.subject_name(name)
			.issuer_name(name)
			.public_key(key.public_key())
			.serial_number(x509.random_serial_number())
			.not_valid_before(now - timedelta(days=1))
			.not_valid_after(now + timedelta(days=1))
			.add_extension(
				x509.KeyUsage(True, True, False, False, False, False, False, False, False), critical=True
			)
			.sign(key, hashes.SHA256())
		)
		with tempfile.TemporaryDirectory() as folder:
			path = Path(folder) / "test.p12"
			path.write_bytes(
				pkcs12.serialize_key_and_certificates(b"test", key, cert, None, serialization.NoEncryption())
			)
			with patch.dict(
				frappe.conf,
				{"esign_pkcs12_path": str(path), "esign_pkcs12_password": "", "esign_timestamp_url": None},
			):
				content, status = seal_pdf(make_pdf())
			self.assertEqual(status, "Sealed")
			reader = PdfFileReader(io.BytesIO(content))
			self.assertEqual(len(reader.embedded_signatures), 1)
			root = asn1_x509.Certificate.load(cert.public_bytes(serialization.Encoding.DER))
			result = validate_pdf_signature(
				reader.embedded_signatures[0],
				signer_validation_context=ValidationContext(trust_roots=[root], allow_fetching=False),
			)
			self.assertTrue(result.intact)
			self.assertTrue(result.valid)
			self.assertTrue(result.trusted)
