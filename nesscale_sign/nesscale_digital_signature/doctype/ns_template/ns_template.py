# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt

from frappe.model.document import Document


class NSTemplate(Document):
	def on_update(self):
		# Keep the auto-create reference-doctype cache (used by the universal
		# doc_events dispatcher) in sync with template changes.
		from nesscale_sign.services.integration_service import clear_trigger_cache

		clear_trigger_cache()

	def on_trash(self):
		from nesscale_sign.services.integration_service import clear_trigger_cache

		clear_trigger_cache()
