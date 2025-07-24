# Copyright (c) 2024, arun and contributors
# For license information, please see license.txt

import frappe

# Monkey patch the email get_contact_list function
def override_email_functions(app_name=None):
    """Override email module functions"""
    import frappe.email
    
    original_get_contact_list = frappe.email.get_contact_list
    
    def custom_get_contact_list(txt, page_length=20, extra_filters=None):
        """Custom get_contact_list without middle_name"""
        filters = [
            ["Contact", "name", "like", "%{0}%".format(txt)],
            ["Contact", "full_name", "like", "%{0}%".format(txt)],
            ["Contact", "company_name", "like", "%{0}%".format(txt)],
            ["Contact Email", "email_id", "like", "%{0}%".format(txt)],
        ]
        
        if extra_filters:
            filters.extend(extra_filters)
        
        # Remove middle_name from search fields
        fields = ["first_name", "last_name", "company_name"]
        contacts = frappe.get_list(
            "Contact",
            fields=["full_name", "`tabContact Email`.email_id"],
            filters=filters,
            page_length=page_length,
            order_by="modified desc"
        )
        
        return contacts
    
    frappe.email.get_contact_list = custom_get_contact_list