# Copyright (c) 2026, Nesscale Solutions Pvt Ltd and contributors
# For license information, please see license.txt
"""Template API endpoints."""

import frappe

from nesscale_sign.api import load
from nesscale_sign.services.template_service import TemplateService


@frappe.whitelist()
def create_template(data: dict | None = None):
	return TemplateService.create(load(data) or {}).as_dict()


@frappe.whitelist()
def get_template(name: str):
	doc = frappe.get_doc("NS Template", name)
	doc.check_permission("read")
	svc = TemplateService(name)
	return {
		"template": doc.as_dict(),
		"fields": svc.get_fields(),
		"page_metrics": svc.page_metrics(),
	}


@frappe.whitelist()
def update_template(name: str, data=None):
	doc = frappe.get_doc("NS Template", name)
	doc.check_permission("write")
	data = load(data) or {}
	for field in (
		"title",
		"description",
		"routing_type",
		"expiry_days",
		"email_subject",
		"email_message",
		"reminder_enabled",
		"organization",
		"tags",
		"auto_create",
		"trigger_doctype",
		"trigger_event",
		"trigger_auto_send",
		"trigger_value_field",
		"trigger_value_to",
		"trigger_date_field",
		"trigger_days",
	):
		if field in data:
			doc.set(field, data[field])
	from nesscale_sign.services.template_service import validate_trigger

	validate_trigger(doc)
	doc.save()
	return doc.as_dict()


@frappe.whitelist()
def set_template_pdf(name: str, file_url: str):
	frappe.get_doc("NS Template", name).check_permission("write")
	return TemplateService(name).set_pdf(file_url).as_dict()


@frappe.whitelist()
def save_template_fields(name: str, fields=None):
	frappe.get_doc("NS Template", name).check_permission("write")
	count = TemplateService(name).save_fields(load(fields) or [])
	return {"saved": count}


@frappe.whitelist()
def save_template_roles(name: str, roles=None):
	frappe.get_doc("NS Template", name).check_permission("write")
	return TemplateService(name).save_roles(load(roles) or []).as_dict()


@frappe.whitelist()
def publish_template(name: str):
	frappe.get_doc("NS Template", name).check_permission("write")
	return TemplateService(name).publish().as_dict()


@frappe.whitelist()
def archive_template(name: str):
	frappe.get_doc("NS Template", name).check_permission("write")
	return TemplateService(name).archive().as_dict()


@frappe.whitelist()
def duplicate_template(name: str, title: str | None = None):
	frappe.get_doc("NS Template", name).check_permission("read")
	return TemplateService(name).duplicate(title).as_dict()


@frappe.whitelist()
def list_templates(
	status: str | None = None, search: str | None = None, start: int = 0, page_length: int = 20
):
	filters = {}
	if status:
		filters["status"] = status
	or_filters = None
	if search:
		or_filters = {"title": ["like", f"%{search}%"], "name": ["like", f"%{search}%"]}
	return frappe.get_list(
		"NS Template",
		filters=filters,
		or_filters=or_filters,
		fields=[
			"name",
			"title",
			"status",
			"organization",
			"page_count",
			"version_count",
			"routing_type",
			"modified",
		],
		order_by="modified desc",
		start=int(start),
		page_length=int(page_length),
	)


@frappe.whitelist()
def preview_pdf(name: str):
	doc = frappe.get_doc("NS Template", name)
	doc.check_permission("read")
	from nesscale_sign.api.envelope import _stream_private_file

	_stream_private_file(doc.pdf_file, f"{doc.name}.pdf")
