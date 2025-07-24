# Copyright (c) 2024, arun and contributors
# For license information, please see license.txt

import frappe
from frappe.core.doctype.user.user import create_contact


def after_insert(doc, method):
    """Override to handle user creation from contact"""
    # Skip contact creation if user was created from a contact
    if not (hasattr(doc, 'flags') and doc.flags.get('created_from_contact')):
        frappe.enqueue(
            create_contact,
            user=doc,
            ignore_mandatory=True,
            now=frappe.flags.in_test or frappe.flags.in_install,
            enqueue_after_commit=True,
        )


def validate_contact_creation(user):
    """Check if contact creation should be skipped"""
    # Skip contact creation if user was created from a contact
    if hasattr(user, 'flags') and user.flags.get('created_from_contact'):
        return False
    
    # Skip for standard users
    if user.name in ["Administrator", "Guest"]:
        return False
        
    return True