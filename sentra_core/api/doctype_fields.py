import frappe
from frappe import _
from typing import Dict, List, Any

@frappe.whitelist()
def get_list_fields(doctype: str) -> Dict[str, Any]:
    """
    Get all available fields for a doctype that can be shown in list views
    
    Args:
        doctype: Name of the DocType (e.g., "Contact", "Lead", etc.)
        
    Returns:
        List of fields with their metadata
    """
    try:
        if not frappe.has_permission(doctype, "read"):
            frappe.throw(_("You don't have permission to access {0}").format(doctype))
            
        meta = frappe.get_meta(doctype)
        
        # Fields to exclude from list views
        excluded_fieldtypes = [
            "Section Break", 
            "Column Break", 
            "Tab Break", 
            "Button", 
            "HTML", 
            "Image", 
            "Attach", 
            "Attach Image",
            "Signature",
            "Password",
            "Geolocation"
        ]
        
        # Standard fields that are always available
        standard_fields = [
            {"fieldname": "name", "label": "ID", "fieldtype": "Data", "in_standard_filter": True},
            {"fieldname": "owner", "label": "Created By", "fieldtype": "Link", "options": "User"},
            {"fieldname": "creation", "label": "Created On", "fieldtype": "Datetime"},
            {"fieldname": "modified", "label": "Last Modified", "fieldtype": "Datetime"},
            {"fieldname": "modified_by", "label": "Modified By", "fieldtype": "Link", "options": "User"},
            {"fieldname": "_user_tags", "label": "Tags", "fieldtype": "Data"},
            {"fieldname": "_liked_by", "label": "Liked By", "fieldtype": "Data"},
            {"fieldname": "_assign", "label": "Assigned To", "fieldtype": "Text"},
            {"fieldname": "_comments", "label": "Comments", "fieldtype": "Text"}
        ]
        
        # Get all DocFields
        doc_fields = []
        for field in meta.fields:
            if field.fieldtype not in excluded_fieldtypes and not field.hidden:
                field_info = {
                    "fieldname": field.fieldname,
                    "label": field.label or field.fieldname,
                    "fieldtype": field.fieldtype,
                    "reqd": field.reqd,
                    "in_list_view": field.in_list_view,
                    "in_standard_filter": field.in_standard_filter,
                    "in_global_search": field.in_global_search
                }
                
                # Add field-specific metadata
                if field.fieldtype == "Select":
                    field_info["options"] = field.options
                elif field.fieldtype in ["Link", "Dynamic Link"]:
                    field_info["options"] = field.options
                elif field.fieldtype in ["Int", "Float", "Currency", "Percent"]:
                    field_info["precision"] = field.precision
                
                # Add depends_on if field visibility depends on other fields
                if field.depends_on:
                    field_info["depends_on"] = field.depends_on
                    
                # For Contact, add type-specific applicability
                if doctype == "Contact" and hasattr(field, 'depends_on') and field.depends_on:
                    # Parse depends_on to determine applicability
                    if "Employee" in field.depends_on:
                        field_info["applicable_to"] = ["Employee"]
                    elif "Vendor" in field.depends_on:
                        field_info["applicable_to"] = ["Vendor"]
                    elif "Customer" in field.depends_on:
                        field_info["applicable_to"] = ["Customer"]
                    else:
                        field_info["applicable_to"] = "all"
                else:
                    field_info["applicable_to"] = "all"
                    
                doc_fields.append(field_info)
        
        # Get Custom Fields
        custom_fields = frappe.get_all("Custom Field",
            filters={"dt": doctype},
            fields=["fieldname", "label", "fieldtype", "options", "reqd", 
                   "in_list_view", "in_standard_filter", "in_global_search", "depends_on"]
        )
        
        for field in custom_fields:
            if field.fieldtype not in excluded_fieldtypes:
                field_info = {
                    "fieldname": field.fieldname,
                    "label": field.label or field.fieldname,
                    "fieldtype": field.fieldtype,
                    "reqd": field.reqd,
                    "in_list_view": field.in_list_view,
                    "in_standard_filter": field.in_standard_filter,
                    "in_global_search": field.in_global_search,
                    "is_custom": True
                }
                
                if field.fieldtype == "Select" and field.options:
                    field_info["options"] = field.options
                elif field.fieldtype in ["Link", "Dynamic Link"] and field.options:
                    field_info["options"] = field.options
                    
                if field.depends_on:
                    field_info["depends_on"] = field.depends_on
                    
                doc_fields.append(field_info)
        
        # Combine all fields
        all_fields = standard_fields + doc_fields
        
        # Get title field
        title_field = meta.title_field
        
        return {
            "success": True,
            "data": {
                "fields": all_fields,
                "title_field": title_field,
                "doctype": doctype,
                "total_fields": len(all_fields)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_quick_entry_fields(doctype: str) -> Dict[str, Any]:
    """
    Get fields that should appear in quick entry forms
    
    Args:
        doctype: Name of the DocType
        
    Returns:
        List of fields for quick entry
    """
    try:
        meta = frappe.get_meta(doctype)
        
        quick_entry_fields = []
        for field in meta.fields:
            if field.in_quick_entry and not field.hidden:
                field_info = {
                    "fieldname": field.fieldname,
                    "label": field.label,
                    "fieldtype": field.fieldtype,
                    "reqd": field.reqd
                }
                
                if field.fieldtype == "Select":
                    field_info["options"] = field.options
                elif field.fieldtype in ["Link", "Dynamic Link"]:
                    field_info["options"] = field.options
                    
                quick_entry_fields.append(field_info)
                
        return {
            "success": True,
            "data": quick_entry_fields
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }