# Copyright (c) 2024, arun and contributors
# For license information, please see license.txt

import frappe
from frappe.model.utils import set_field_property


def execute():
    """Hide phone field from User doctype"""
    # Option 1: Hide the field (safer approach)
    frappe.db.sql("""
        UPDATE `tabDocField` 
        SET hidden = 1 
        WHERE parent = 'User' 
        AND fieldname = 'phone'
    """)
    
    # Option 2: Use Property Setter to hide it
    from frappe.custom.doctype.property_setter.property_setter import make_property_setter
    make_property_setter("User", "phone", "hidden", 1, "Check")
    
    # Clear cache
    frappe.clear_cache(doctype="User")