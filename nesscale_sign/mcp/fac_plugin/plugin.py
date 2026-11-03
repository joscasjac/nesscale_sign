"""Open E-Sign tools for Frappe Assistant Core."""

from frappe_assistant_core.plugins.base_plugin import BasePlugin


class OpenESignPlugin(BasePlugin):
	def get_info(self):
		return {
			"name": "open_esign",
			"display_name": "Open E-Sign",
			"description": "Build and manage signing documents",
			"version": "2.0.0",
			"dependencies": ["nesscale_sign"],
		}

	def get_tools(self):
		from nesscale_sign.mcp.tools import TOOLS

		return list(TOOLS)

	def validate_environment(self):
		return True, None
