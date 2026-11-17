import frappe
from frappe.translate import get_all_translations


@frappe.whitelist(allow_guest=True, methods=["GET"])
def get_translations(lang: str | None = None) -> dict:
	"""Translations for the Vue SPA, keyed by English source string.

	Signed-in users get their own language; guest signers get the language the
	page was rendered in (browser Accept-Language / preferred_language cookie).
	"""
	if frappe.session.user != "Guest" or not lang or not frappe.db.exists("Language", lang):
		lang = frappe.local.lang
	if not lang or lang == "en" or lang.startswith("en-"):
		return {}
	return get_all_translations(lang)
