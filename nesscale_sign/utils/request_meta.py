# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Best-effort extraction of request metadata for audit logging.

Kept dependency-free: a small user-agent heuristic covers the common browsers
and operating systems without pulling in a parsing library. Country is read
from a reverse-proxy header when present (Cloudflare / common CDNs).
"""

import frappe


def get_request_ip() -> str:
	try:
		return frappe.local.request_ip or ""
	except Exception:
		return ""


def get_user_agent() -> str:
	try:
		return frappe.request.headers.get("User-Agent", "") if frappe.request else ""
	except Exception:
		return ""


def get_country() -> str:
	if not getattr(frappe, "request", None):
		return ""
	headers = frappe.request.headers
	for header in ("CF-IPCountry", "X-Country-Code", "X-Geo-Country"):
		value = headers.get(header)
		if value and value != "XX":
			return value
	return ""


def parse_user_agent(ua: str | None = None) -> dict:
	ua = (ua if ua is not None else get_user_agent()) or ""
	low = ua.lower()

	browser = "Unknown"
	for token, name in (
		("edg/", "Edge"),
		("opr/", "Opera"),
		("chrome/", "Chrome"),
		("crios/", "Chrome"),
		("firefox/", "Firefox"),
		("fxios/", "Firefox"),
		("safari/", "Safari"),
	):
		if token in low:
			browser = name
			break

	os_name = "Unknown"
	for token, name in (
		("windows", "Windows"),
		("iphone", "iOS"),
		("ipad", "iPadOS"),
		("mac os", "macOS"),
		("macintosh", "macOS"),
		("android", "Android"),
		("linux", "Linux"),
	):
		if token in low:
			os_name = name
			break

	device = "Mobile" if any(t in low for t in ("mobile", "iphone", "android")) else "Desktop"

	return {"browser": browser, "os": os_name, "device": device}


def collect() -> dict:
	"""Return a single dict with all request metadata for audit/session records."""
	ua = get_user_agent()
	parsed = parse_user_agent(ua)
	return {
		"ip_address": get_request_ip(),
		"user_agent": ua,
		"country": get_country(),
		"browser": parsed["browser"],
		"os": parsed["os"],
		"device": parsed["device"],
	}
