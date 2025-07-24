# Copyright (c) 2024, arun and contributors
# For license information, please see license.txt

import frappe
from frappe import _


@frappe.whitelist()
def get_list_settings(doctype, settings_name=None):
    """Get list settings for a specific view"""
    if not settings_name:
        return None

    try:
        return frappe.get_cached_doc("List View Settings", f"{doctype}-{settings_name}")
    except frappe.DoesNotExistError:
        frappe.clear_messages()


@frappe.whitelist()
def set_list_settings(doctype, settings_name, values):
    """Save list settings for a specific view"""
    # Make sure that settings_name is not None or ""
    if not settings_name:
        settings_name = "default"

    values = frappe.parse_json(values)
    # Don't allow this to be updated from client script
    values.pop("doctype_name", None)

    try:
        doc = frappe.get_doc("List View Settings", f"{doctype}-{settings_name}")
    except frappe.DoesNotExistError:
        doc = frappe.new_doc("List View Settings")
        doc.doctype_name = doctype
        doc.settings_name = settings_name
        frappe.clear_messages()
    
    doc.update(values)
    doc.save()


@frappe.whitelist()
def get_all_list_settings(doctype):
    """Get all saved list settings for a doctype"""
    return frappe.get_all(
        "List View Settings", 
        filters={"doctype_name": doctype}, 
        fields=["name", "settings_name"]
    )