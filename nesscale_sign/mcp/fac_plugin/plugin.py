"""Open E-Sign tools for Frappe Assistant Core."""

from frappe_assistant_core.plugins.base_plugin import BasePlugin


class OpenESignPlugin(BasePlugin):
	def get_info(self):
		return {
			"name": "open_esign",
			"display_name": "Open E-Sign",
			"description": "Build and manage signing documents",
			"version": "1.0.0",
			"dependencies": ["nesscale_sign"],
		}

	def get_tools(self):
		return [
			"esign_builder_guide",
			"esign_list_templates",
			"esign_get_template",
			"esign_list_documents",
			"esign_get_document",
			"esign_create_draft",
			"esign_update_draft",
			"esign_send_document",
			"esign_revise_unsigned",
		]

	def validate_environment(self):
		return True, None
