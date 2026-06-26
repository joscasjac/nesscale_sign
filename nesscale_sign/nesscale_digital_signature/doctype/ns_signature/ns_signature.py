# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt

import hashlib

from frappe.model.document import Document


class NSSignature(Document):
	"""A captured signature (drawn, typed, or uploaded).

	The image is always stored as a private file. An integrity hash over the
	stored image content is recorded so the signature can be verified against
	the embedded artifact in the final PDF.
	"""

	def before_insert(self):
		self.hash = self._compute_image_hash()

	def _compute_image_hash(self) -> str:
		if not self.signature_image:
			return ""
		from nesscale_sign.utils.files import read_file_content

		try:
			return hashlib.sha256(read_file_content(self.signature_image)).hexdigest()
		except Exception:
			# Fall back to hashing the file URL + typed text if the file is not
			# yet resolvable on disk (e.g. created in same transaction).
			seed = f"{self.signature_image}|{self.typed_text or ''}"
			return hashlib.sha256(seed.encode("utf-8")).hexdigest()
