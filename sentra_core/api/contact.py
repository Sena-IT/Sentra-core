import frappe
from frappe import _
from typing import Dict, List, Optional, Any
import json
import csv
import io
import base64
import re
from datetime import datetime
from sentra_core.api.create import (
    create_document,
    bulk_upload_documents,
    create_document_from_unstructured_data
)

# ============ CREATE APIs ============
# Create APIs have been moved to api/create.py for generic doctype support
# These are wrapper functions for backward compatibility

@frappe.whitelist()
def create_contact(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a single contact
    
    Args:
        data: Contact data including fields like first_name, last_name, email_id, etc.
        
    Returns:
        Created contact document
    """
    return create_document("Contact", data)


@frappe.whitelist()
def bulk_upload_contacts(file_content: str, file_type: str = "csv") -> Dict[str, Any]:
    """
    Bulk upload contacts from CSV/Excel
    
    Args:
        file_content: Base64 encoded file content
        file_type: Type of file (csv, xlsx)
        
    Returns:
        Upload results with success/failure counts
    """
    return bulk_upload_documents("Contact", file_content, file_type)


@frappe.whitelist()
def create_contact_from_ai(unstructured_data: str, data_type: str = "text") -> Dict[str, Any]:
    """
    Create contact from unstructured data using AI parsing
    
    Args:
        unstructured_data: Raw text, business card info, email signature, etc.
        data_type: Type of data (text, business_card, email_signature)
        
    Returns:
        Created contact or parsed data for review
    """
    # Contact-specific parsing rules
    parsing_rules = {
        "email_id": {"pattern": r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"},
        "mobile_no": {"pattern": r"(\+?\d[\d\s\-\(\)]{9,})"},
    }
    return create_document_from_unstructured_data("Contact", unstructured_data, data_type, parsing_rules)


# ============ READ APIs ============

@frappe.whitelist()
def get_contacts(
    filters: Optional[Dict[str, Any]] = None,
    fields: Optional[List[str]] = None,
    order_by: str = "modified desc",
    page: int = 1,
    page_size: int = 20,
    search_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get list of contacts with filtering, sorting, and pagination
    
    Args:
        filters: Field filters (e.g., {"contact_type": "Customer"})
        fields: Fields to return
        order_by: Sort order
        page: Page number
        page_size: Items per page
        search_text: Text to search across searchable fields
        
    Returns:
        Paginated list of contacts
    """
    # Use the generic list API
    from sentra_core.api.read import get_list
    
    # If no fields specified, use Contact-specific defaults
    if not fields:
        fields = [
            "name", "full_name", "first_name", "last_name", 
            "email_id", "mobile_no", "contact_type", "contact_category",
            "city", "state", "modified", "creation"
        ]
    
    result = get_list(
        doctype="Contact",
        filters=filters,
        fields=fields,
        order_by=order_by,
        page=page,
        page_size=page_size,
        search_text=search_text
    )
    
    # Rename "documents" to "contacts" for backward compatibility
    if result.get("success") and "data" in result:
        result["data"]["contacts"] = result["data"].pop("documents", [])
    
    return result


# Contact detail functions moved to api/contact/read.py


@frappe.whitelist()
def search_contacts_ai(query: str) -> Dict[str, Any]:
    """
    Search contacts using natural language
    
    Args:
        query: Natural language search query (e.g., "all vendors in Mumbai")
        
    Returns:
        Matching contacts
    """
    try:
        # This is a placeholder for AI integration
        # For now, implement basic keyword extraction
        
        filters = {}
        
        # Basic keyword matching
        query_lower = query.lower()
        
        # Location matching
        cities = ["mumbai", "delhi", "bangalore", "chennai", "kolkata", "pune"]
        for city in cities:
            if city in query_lower:
                filters["city"] = city.capitalize()
                break
                
        # Contact type matching
        if "vendor" in query_lower or "supplier" in query_lower:
            filters["contact_type"] = "Vendor"
        elif "customer" in query_lower or "client" in query_lower:
            filters["contact_type"] = "Customer"
        elif "employee" in query_lower:
            filters["contact_type"] = "Employee"
            
        # Status matching
        if "inactive" in query_lower or "passive" in query_lower:
            filters["status"] = "Passive"
        elif "active" in query_lower:
            filters["status"] = "Active"
            
        # Use the get_contacts function with extracted filters
        return get_contacts(filters=filters)
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


# ============ UPDATE APIs ============

@frappe.whitelist()
def update_contact(contact_name: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update a single contact
    
    Args:
        contact_name: Contact ID/name
        data: Fields to update
        
    Returns:
        Updated contact document
    """
    try:
        if isinstance(data, str):
            data = json.loads(data)
            
        contact = frappe.get_doc("Contact", contact_name)
        
        # Update fields
        for field, value in data.items():
            if hasattr(contact, field):
                setattr(contact, field, value)
                
        contact.save()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Contact updated successfully"),
            "data": contact.as_dict()
        }
    except Exception as e:
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def export_contacts(filters: Optional[Dict[str, Any]] = None, format: str = "csv") -> Dict[str, Any]:
    """
    Export contacts to CSV/Excel
    
    Args:
        filters: Filters to apply
        format: Export format (csv, xlsx)
        
    Returns:
        File content or download URL
    """
    try:
        # Get contacts using existing function
        result = get_contacts(filters=filters, page_size=10000)  # Large page size for export
        
        if not result["success"]:
            return result
            
        contacts = result["data"]["contacts"]
        
        if format == "csv":
            output = io.StringIO()
            if contacts:
                writer = csv.DictWriter(output, fieldnames=contacts[0].keys())
                writer.writeheader()
                writer.writerows(contacts)
            content = output.getvalue()
            
        else:  # xlsx
            import pandas as pd
            df = pd.DataFrame(contacts)
            output = io.BytesIO()
            df.to_excel(output, index=False)
            content = base64.b64encode(output.getvalue()).decode()
            
        return {
            "success": True,
            "data": {
                "content": content,
                "filename": f"contacts_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format}",
                "format": format
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def bulk_update_contacts(updates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Bulk update multiple contacts
    
    Args:
        updates: List of updates with contact_name and fields to update
        
    Returns:
        Update results
    """
    try:
        if isinstance(updates, str):
            updates = json.loads(updates)
            
        success_count = 0
        errors = []
        
        for update in updates:
            try:
                contact_name = update.pop("contact_name", update.pop("name", None))
                if not contact_name:
                    raise ValueError("Contact name is required")
                    
                result = update_contact(contact_name, update)
                if result["success"]:
                    success_count += 1
                else:
                    errors.append({
                        "contact": contact_name,
                        "error": result["message"]
                    })
            except Exception as e:
                errors.append({
                    "contact": contact_name,
                    "error": str(e)
                })
                
        return {
            "success": True,
            "message": _(f"Updated {success_count} contacts"),
            "data": {
                "success_count": success_count,
                "error_count": len(errors),
                "errors": errors
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


# ============ DELETE APIs ============

@frappe.whitelist()
def delete_contact(contact_name: str) -> Dict[str, Any]:
    """
    Delete a single contact
    
    Args:
        contact_name: Contact ID/name
        
    Returns:
        Deletion status
    """
    try:
        frappe.delete_doc("Contact", contact_name)
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Contact deleted successfully")
        }
    except Exception as e:
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def bulk_delete_contacts(contact_names: List[str]) -> Dict[str, Any]:
    """
    Delete multiple contacts
    
    Args:
        contact_names: List of contact IDs/names
        
    Returns:
        Deletion results
    """
    try:
        if isinstance(contact_names, str):
            contact_names = json.loads(contact_names)
            
        success_count = 0
        errors = []
        
        for contact_name in contact_names:
            try:
                frappe.delete_doc("Contact", contact_name)
                success_count += 1
            except Exception as e:
                errors.append({
                    "contact": contact_name,
                    "error": str(e)
                })
                
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _(f"Deleted {success_count} contacts"),
            "data": {
                "success_count": success_count,
                "error_count": len(errors),
                "errors": errors
            }
        }
    except Exception as e:
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def delete_contacts_ai(query: str, dry_run: bool = True) -> Dict[str, Any]:
    """
    Delete contacts based on natural language query
    
    Args:
        query: Natural language deletion query (e.g., "delete all inactive contacts from 2020")
        dry_run: If True, only return what would be deleted without actually deleting
        
    Returns:
        Deletion results or preview
    """
    try:
        # First, search for contacts matching the query
        search_result = search_contacts_ai(query)
        
        if not search_result["success"]:
            return search_result
            
        contacts = search_result["data"]["contacts"]
        contact_names = [c["name"] for c in contacts]
        
        if dry_run:
            return {
                "success": True,
                "message": _(f"Found {len(contacts)} contacts matching your query"),
                "data": {
                    "contacts": contacts,
                    "would_delete": len(contacts),
                    "dry_run": True
                }
            }
        else:
            return bulk_delete_contacts(contact_names)
            
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


# ============ UTILITY APIs ============

@frappe.whitelist()
def get_contact_meta() -> Dict[str, Any]:
    """
    Get metadata about Contact doctype (fields, types, options)
    
    Returns:
        Contact doctype metadata
    """
    try:
        meta = frappe.get_meta("Contact")
        
        fields = []
        for field in meta.fields:
            if field.fieldtype not in ["Section Break", "Column Break", "HTML"]:
                fields.append({
                    "fieldname": field.fieldname,
                    "label": field.label,
                    "fieldtype": field.fieldtype,
                    "options": field.options,
                    "reqd": field.reqd,
                    "unique": field.unique,
                    "default": field.default
                })
                
        return {
            "success": True,
            "data": {
                "fields": fields,
                "title_field": meta.title_field,
                "search_fields": meta.search_fields.split(",") if meta.search_fields else [],
                "sort_field": meta.sort_field,
                "sort_order": meta.sort_order
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }