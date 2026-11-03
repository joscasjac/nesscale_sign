"""Optional Frappe Assistant Core adapter, loaded only by that connector."""

from .tools import definitions, execute


def make_tool(name):
	from frappe_assistant_core.core.base_tool import BaseTool

	spec = next(item for item in definitions() if item["name"] == name)

	class ESignTool(BaseTool):
		def __init__(self):
			super().__init__()
			self.name = name
			self.description = spec["description"]
			self.inputSchema = spec["inputSchema"]
			self.annotations = spec["annotations"]
			self.requires_permission = "NS Envelope"
			self.source_app = "nesscale_sign"
			self.category = "E-Sign"

		def to_mcp_format(self):
			return {**super().to_mcp_format(), "annotations": self.annotations}

		def _sanitize_arguments(self, arguments):
			# Documents, image bytes and nested SMTP credentials are confidential.
			return {"argument_keys": sorted(arguments), "values_redacted": True}

		def _sanitize_data(self, data):
			return {"output_redacted": True}

		def execute(self, arguments):
			# FAC converts errors to responses; rollback partial file/draft writes first.
			import frappe

			frappe.db.savepoint("esign_tool")
			try:
				return execute(name, arguments)
			except Exception as exc:
				frappe.db.rollback(save_point="esign_tool")
				if name in ("esign_create_email_account", "esign_update_email_account"):
					raise frappe.ValidationError(
						"Email account operation failed. Check the account settings in ERPNext."
					) from None
				if isinstance(exc, (frappe.PermissionError, frappe.ValidationError)):
					raise
				# FAC's unexpected-error path includes raw arguments in Error Log.
				# Convert without including confidential input or exception values.
				raise frappe.ValidationError(
					"E-sign operation failed ("
					+ type(exc).__name__
					+ "). Inspect the document in ERPNext before retrying."
				) from None

	return ESignTool
