import frappe
from frappe import _
from typing import Dict, List, Optional, Any
import json
import csv
import io
import base64
from datetime import datetime

# ============ CREATE APIs ============

@frappe.whitelist()
def create_contact(data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a single contact
    
    Args:
        data: Contact data including fields like first_name, last_name, email_id, etc.
        
    Returns:
        Created contact document
    """
    try:
        # Parse data if it's a string
        if isinstance(data, str):
            data = json.loads(data)
            
        # Create contact document
        contact = frappe.get_doc({
            "doctype": "Contact",
            **data
        })
        
        contact.insert()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Contact created successfully"),
            "data": contact.as_dict()
        }
    except Exception as e:
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


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
    try:
        import base64
        import pandas as pd
        
        # Decode file content
        decoded = base64.b64decode(file_content)
        
        # Parse based on file type
        if file_type == "csv":
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(decoded))
            
        success_count = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                contact_data = row.to_dict()
                # Remove NaN values
                contact_data = {k: v for k, v in contact_data.items() if pd.notna(v)}
                
                contact = frappe.get_doc({
                    "doctype": "Contact",
                    **contact_data
                })
                contact.insert()
                success_count += 1
            except Exception as e:
                errors.append({
                    "row": idx + 2,  # +2 for header and 0-index
                    "error": str(e)
                })
                
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _(f"Uploaded {success_count} contacts successfully"),
            "data": {
                "success_count": success_count,
                "error_count": len(errors),
                "errors": errors[:10]  # Return first 10 errors
            }
        }
    except Exception as e:
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


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
    try:
        # This is a placeholder - integrate with your AI service
        # For now, implement basic parsing logic
        
        parsed_data = {
            "doctype": "Contact"
        }
        
        # Basic parsing example
        lines = unstructured_data.strip().split('\n')
        for line in lines:
            line = line.strip()
            if '@' in line:  # Email
                parsed_data['email_id'] = line
            elif line.startswith('+') or any(char.isdigit() for char in line):  # Phone
                if len([char for char in line if char.isdigit()]) >= 10:
                    parsed_data['mobile_no'] = line
            # Add more parsing logic as needed
            
        return {
            "success": True,
            "message": _("Data parsed successfully"),
            "data": parsed_data,
            "require_confirmation": True  # Frontend should confirm before creating
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


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
    try:
        # Parse parameters if they're strings
        if isinstance(filters, str):
            filters = json.loads(filters) if filters else {}
        if isinstance(fields, str):
            fields = json.loads(fields) if fields else None
            
        # Default fields if not specified
        if not fields:
            fields = [
                "name", "full_name", "first_name", "last_name", 
                "email_id", "mobile_no", "contact_type", "contact_category",
                "city", "state", "modified", "creation"
            ]
            
        # Build filters for Frappe API
        api_filters = filters.copy() if filters else {}
        
        # Handle search text
        or_filters = []
        if search_text:
            search_fields = ["full_name", "email_id", "mobile_no", "city"]
            for field in search_fields:
                or_filters.append([field, "like", f"%{search_text}%"])
        
        # Get total count
        count_filters = api_filters.copy()
        if or_filters:
            # Frappe's get_all with or_filters
            total_count = len(frappe.get_all("Contact",
                filters=count_filters,
                or_filters=or_filters,
                pluck="name"
            ))
        else:
            total_count = frappe.db.count("Contact", filters=count_filters)
        
        # Get paginated results
        offset = (page - 1) * page_size
        
        if or_filters:
            contacts = frappe.get_all("Contact",
                filters=api_filters,
                or_filters=or_filters,
                fields=fields,
                order_by=order_by,
                start=offset,
                page_length=page_size
            )
        else:
            contacts = frappe.get_all("Contact",
                filters=api_filters,
                fields=fields,
                order_by=order_by,
                start=offset,
                page_length=page_size
            )
        
        return {
            "success": True,
            "data": {
                "contacts": contacts,
                "pagination": {
                    "total": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total_count + page_size - 1) // page_size
                }
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_contact_detail(contact_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a single contact
    
    Args:
        contact_name: Contact ID/name
        
    Returns:
        Complete contact information including linked data
    """
    try:
        contact = frappe.get_doc("Contact", contact_name)
        contact_dict = contact.as_dict()
        
        # Add linked information
        # Get linked documents
        links = frappe.get_all("Dynamic Link", 
            filters={
                "link_doctype": "Contact",
                "link_name": contact_name
            },
            fields=["parent", "parenttype", "link_doctype", "link_name"]
        )
        
        contact_dict["linked_documents"] = links
        
        # Get activities/communications
        communications = frappe.get_all("Communication",
            filters={
                "reference_doctype": "Contact",
                "reference_name": contact_name
            },
            fields=["name", "subject", "sent_or_received", "communication_date"],
            order_by="communication_date desc",
            limit=10
        )
        
        contact_dict["recent_communications"] = communications
        
        return {
            "success": True,
            "data": contact_dict
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


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