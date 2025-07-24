# Copyright (c) 2024, arun and contributors
# For license information, please see license.txt

import frappe
from frappe.custom.doctype.custom_field.custom_field import create_custom_fields
from frappe.custom.doctype.property_setter.property_setter import make_property_setter


def after_install():
    """Create custom fields after app installation"""
    # Create custom fields
    create_contact_custom_fields()
    create_communication_custom_fields()
    create_property_setters()
    
    # Clear cache after creating custom fields
    frappe.clear_cache()


def create_contact_custom_fields():
    """Create custom fields for Contact DocType"""
    # Check if fields already exist and skip if they do
    existing_custom_fields = frappe.get_all("Custom Field", 
        filters={"dt": "Contact"}, 
        pluck="fieldname")
    
    # Also check standard fields
    meta = frappe.get_meta("Contact")
    existing_standard_fields = [f.fieldname for f in meta.fields]
    
    # Combine both lists
    existing_fields = existing_custom_fields + existing_standard_fields
    
    custom_fields = {
        "Contact": [
            {
                "fieldname": "contact_type",
                "fieldtype": "Link",
                "label": "Contact Type",
                "options": "Contact Type",
                "insert_after": "user",
                "in_list_view": 1
            },
            {
                "fieldname": "contact_category",
                "fieldtype": "Link",
                "label": "Contact Category",
                "options": "Contact Category",
                "insert_after": "contact_type",
                "in_list_view": 1
            },
            {
                "fieldname": "representatives",
                "fieldtype": "Table",
                "label": "Representatives",
                "options": "Organization Representative",
                "insert_after": "contact_category",
                "depends_on": "eval:doc.contact_category == 'Organization'"
            },
            {
                "fieldname": "personal_details_section",
                "fieldtype": "Section Break",
                "label": "Personal Details",
                "insert_after": "representatives",
                "collapsible": 1
            },
            {
                "fieldname": "dob",
                "fieldtype": "Date",
                "label": "Date of Birth",
                "insert_after": "personal_details_section"
            },
            {
                "fieldname": "notes",
                "fieldtype": "Long Text",
                "label": "Notes",
                "insert_after": "dob"
            },
            {
                "fieldname": "address_details_section",
                "fieldtype": "Section Break",
                "label": "Address Details",
                "insert_after": "notes",
                "collapsible": 1
            },
            {
                "fieldname": "address_line1",
                "fieldtype": "Data",
                "label": "Address Line 1",
                "insert_after": "address_details_section"
            },
            {
                "fieldname": "address_line2",
                "fieldtype": "Data",
                "label": "Address Line 2",
                "insert_after": "address_line1"
            },
            {
                "fieldname": "city",
                "fieldtype": "Data",
                "label": "City",
                "insert_after": "address_line2"
            },
            {
                "fieldname": "state",
                "fieldtype": "Data",
                "label": "State",
                "insert_after": "city"
            },
            {
                "fieldname": "country",
                "fieldtype": "Data",
                "label": "Country",
                "insert_after": "state"
            },
            {
                "fieldname": "pincode",
                "fieldtype": "Data",
                "label": "Pincode",
                "insert_after": "country"
            },
            {
                "fieldname": "employee_details_section",
                "fieldtype": "Section Break",
                "label": "Employee Details",
                "insert_after": "pincode",
                "collapsible": 1
            },
            {
                "fieldname": "designation",
                "fieldtype": "Data",
                "label": "Designation",
                "insert_after": "employee_details_section"
            },
            {
                "fieldname": "employee_code",
                "fieldtype": "Data",
                "label": "Employee Code",
                "insert_after": "designation"
            },
            {
                "fieldname": "date_of_joining",
                "fieldtype": "Date",
                "label": "Date of Joining",
                "insert_after": "employee_code"
            },
            {
                "fieldname": "employee_status",
                "fieldtype": "Select",
                "label": "Employee Status",
                "options": "Active\nInactive\nOn Leave",
                "insert_after": "date_of_joining"
            },
            {
                "fieldname": "manager",
                "fieldtype": "Link",
                "label": "Manager",
                "options": "Contact",
                "insert_after": "employee_status"
            },
            {
                "fieldname": "work_email",
                "fieldtype": "Data",
                "label": "Work Email",
                "insert_after": "manager"
            },
            {
                "fieldname": "social_media_section",
                "fieldtype": "Section Break",
                "label": "Social Media",
                "insert_after": "work_email",
                "collapsible": 1
            },
            {
                "fieldname": "instagram",
                "fieldtype": "Data",
                "label": "Instagram",
                "insert_after": "social_media_section"
            },
            {
                "fieldname": "website",
                "fieldtype": "Data",
                "label": "Website",
                "insert_after": "instagram"
            },
            {
                "fieldname": "gstin",
                "fieldtype": "Data",
                "label": "GSTIN",
                "insert_after": "website"
            },
            {
                "fieldname": "vendor_type",
                "fieldtype": "Select",
                "label": "Vendor Type",
                "options": "\nSupplier\nService Provider\nContractor",
                "insert_after": "gstin"
            }
        ]
    }
    
    # Filter out fields that already exist
    for doctype, fields in custom_fields.items():
        filtered_fields = []
        for field in fields:
            if field["fieldname"] not in existing_fields:
                filtered_fields.append(field)
            else:
                print(f"Field {field['fieldname']} already exists in {doctype}, skipping...")
        
        if filtered_fields:
            create_custom_fields({doctype: filtered_fields})


def create_communication_custom_fields():
    """Create custom fields for Communication DocType"""
    # Add any custom fields for Communication here
    custom_fields = {
        "Communication": [
            # Add custom fields as needed
        ]
    }
    
    if custom_fields.get("Communication"):
        create_custom_fields(custom_fields)


def create_property_setters():
    """Create property setters for customizations"""
    # Contact property setters
    make_property_setter("Contact", "first_name", "mandatory_depends_on", "1", "Data")
    make_property_setter("Contact", "last_name", "depends_on", "eval:doc.contact_category != 'Organization'", "Data")
    
    # List View Settings property setters
    make_property_setter("List View Settings", None, "autoname", "format:{doctype_name}-{settings_name}", "Data")
    
    # Remove phone field from User
    # This is handled in patches instead