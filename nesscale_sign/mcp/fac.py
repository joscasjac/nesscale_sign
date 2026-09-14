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

		def execute(self, arguments):
			# FAC converts errors to responses; rollback partial file/draft writes first.
			import frappe

			frappe.db.savepoint("esign_tool")
			try:
				return execute(name, arguments)
			except Exception:
				frappe.db.rollback(save_point="esign_tool")
				raise

	return ESignTool
