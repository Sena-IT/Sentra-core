import frappe
from frappe import _
from typing import Dict, List, Optional, Any
import json
import base64
import io
import csv
from datetime import datetime

# ============ BULK CREATE ============

@frappe.whitelist()
def bulk_create_contacts(contacts: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create multiple contacts in a single operation
    
    Args:
        contacts: List of contact data dictionaries
        
    Returns:
        Results with success/failure counts and details
    """
    try:
        if isinstance(contacts, str):
            contacts = json.loads(contacts)
        
        if len(contacts) > 500:
            frappe.throw(_("Bulk create is limited to 500 contacts per request"))
        
        results = {
            "success_count": 0,
            "failed_count": 0,
            "created_contacts": [],
            "failed_contacts": [],
            "total_requested": len(contacts)
        }
        
        for idx, contact_data in enumerate(contacts):
            try:
                # Create contact document
                contact = frappe.get_doc({
                    "doctype": "Contact",
                    **contact_data
                })
                
                contact.insert()
                
                results["success_count"] += 1
                results["created_contacts"].append({
                    "index": idx,
                    "name": contact.name,
                    "full_name": contact.full_name
                })
                
            except Exception as e:
                results["failed_count"] += 1
                results["failed_contacts"].append({
                    "index": idx,
                    "data": contact_data,
                    "error": str(e)
                })
        
        # Commit only if we have any successes
        if results["success_count"] > 0:
            frappe.db.commit()
        else:
            frappe.db.rollback()
        
        return {
            "success": True,
            "message": _("Created {0} contacts, {1} failed").format(
                results["success_count"], results["failed_count"]
            ),
            "data": results
        }
        
    except Exception as e:
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def bulk_create_from_csv(file_content: str, file_type: str = "csv", validate_only: bool = False) -> Dict[str, Any]:
    """
    Create contacts from CSV/Excel file
    
    Args:
        file_content: Base64 encoded file content
        file_type: File type (csv, xlsx)
        validate_only: If True, only validate without creating
        
    Returns:
        Import results with validation details
    """
    try:
        # Decode file content
        decoded = base64.b64decode(file_content)
        
        # Parse based on file type
        if file_type.lower() == "csv":
            df_data = parse_csv_content(decoded.decode('utf-8'))
        else:
            # For Excel, would need pandas - using CSV for now
            df_data = parse_csv_content(decoded.decode('utf-8'))
        
        # Validate data
        validation_results = validate_bulk_contact_data(df_data)
        
        if validate_only:
            return {
                "success": True,
                "message": _("Validation completed"),
                "data": {
                    "total_rows": len(df_data),
                    "valid_rows": validation_results["valid_count"],
                    "invalid_rows": validation_results["invalid_count"],
                    "validation_errors": validation_results["errors"]
                }
            }
        
        # Create contacts from valid data
        valid_contacts = validation_results["valid_data"]
        
        if not valid_contacts:
            return {
                "success": False,
                "message": _("No valid contacts found to create"),
                "data": validation_results
            }
        
        # Use bulk_create_contacts for actual creation
        create_result = bulk_create_contacts(valid_contacts)
        
        # Combine with validation results
        create_result["data"]["validation_errors"] = validation_results["errors"]
        
        return create_result
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


# ============ BULK UPDATE ============

@frappe.whitelist()
def bulk_update_contacts(updates: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Update multiple contacts using Frappe's bulk_update with enhanced error handling
    
    Args:
        updates: List of update data with contact_name and fields to update
        
    Returns:
        Update results with detailed error information
    """
    try:
        if isinstance(updates, str):
            updates = json.loads(updates)
        
        if len(updates) > 500:
            frappe.throw(_("Bulk update is limited to 500 contacts per request"))
        
        # Prepare data for Frappe's bulk_update
        bulk_docs = []
        for update in updates:
            if "contact_name" in update:
                doc_data = {
                    "doctype": "Contact",
                    "docname": update.pop("contact_name"),
                    **update
                }
            elif "name" in update:
                doc_data = {
                    "doctype": "Contact",
                    "docname": update.pop("name"),
                    **update
                }
            else:
                continue
            
            bulk_docs.append(doc_data)
        
        # Use Frappe's bulk_update
        from frappe.client import bulk_update
        result = bulk_update(json.dumps(bulk_docs))
        
        # Enhanced response formatting
        success_count = len(bulk_docs) - len(result.get("failed_docs", []))
        
        return {
            "success": True,
            "message": _("Updated {0} contacts, {1} failed").format(
                success_count, len(result.get("failed_docs", []))
            ),
            "data": {
                "success_count": success_count,
                "failed_count": len(result.get("failed_docs", [])),
                "total_requested": len(bulk_docs),
                "failed_docs": result.get("failed_docs", [])
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


# ============ BULK DELETE ============

@frappe.whitelist()
def bulk_delete_contacts(contact_names: List[str], force_delete: bool = False) -> Dict[str, Any]:
    """
    Delete multiple contacts with dependency checking
    
    Args:
        contact_names: List of contact IDs to delete
        force_delete: If True, skip some dependency checks (use carefully)
        
    Returns:
        Deletion results with detailed error information
    """
    try:
        if isinstance(contact_names, str):
            contact_names = json.loads(contact_names)
        
        if len(contact_names) > 100:
            frappe.throw(_("Bulk delete is limited to 100 contacts per request for safety"))
        
        results = {
            "success_count": 0,
            "failed_count": 0,
            "deleted_contacts": [],
            "failed_contacts": [],
            "total_requested": len(contact_names)
        }
        
        for contact_name in contact_names:
            try:
                # Check if contact exists
                if not frappe.db.exists("Contact", contact_name):
                    results["failed_count"] += 1
                    results["failed_contacts"].append({
                        "name": contact_name,
                        "error": _("Contact not found")
                    })
                    continue
                
                # Get contact for validation
                contact = frappe.get_doc("Contact", contact_name)
                
                # Check dependencies unless force delete
                if not force_delete:
                    # Use our existing validation
                    from sentra_core.overrides.contact import validate_delete_permissions
                    try:
                        validate_delete_permissions(contact)
                    except Exception as validation_error:
                        results["failed_count"] += 1
                        results["failed_contacts"].append({
                            "name": contact_name,
                            "full_name": contact.full_name,
                            "error": str(validation_error)
                        })
                        continue
                
                # Delete the contact
                frappe.delete_doc("Contact", contact_name)
                
                results["success_count"] += 1
                results["deleted_contacts"].append({
                    "name": contact_name,
                    "full_name": contact.full_name
                })
                
            except Exception as e:
                results["failed_count"] += 1
                results["failed_contacts"].append({
                    "name": contact_name,
                    "error": str(e)
                })
        
        # Commit changes
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("Deleted {0} contacts, {1} failed").format(
                results["success_count"], results["failed_count"]
            ),
            "data": results
        }
        
    except Exception as e:
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


# ============ BULK EXPORT ============

@frappe.whitelist()
def bulk_export_contacts(
    filters: Optional[Dict[str, Any]] = None,
    fields: Optional[List[str]] = None,
    format: str = "csv"
) -> Dict[str, Any]:
    """
    Export contacts in bulk with filtering
    
    Args:
        filters: Filters to apply
        fields: Fields to export
        format: Export format (csv, xlsx)
        
    Returns:
        Export data or file download info
    """
    try:
        if isinstance(filters, str):
            filters = json.loads(filters) if filters else {}
        if isinstance(fields, str):
            fields = json.loads(fields) if fields else None
        
        # Default fields if not specified
        if not fields:
            fields = [
                "name", "full_name", "first_name", "last_name",
                "email_id", "mobile_no", "phone", "contact_type", "contact_category",
                "city", "state", "country", "pincode", "gstin",
                "employee_code", "designation", "company_name",
                "creation", "modified"
            ]
        
        # Build query conditions
        conditions = ["1=1"]
        values = []
        
        if filters:
            for field, value in filters.items():
                if isinstance(value, list):
                    placeholders = ",".join(["%s"] * len(value))
                    conditions.append(f"`{field}` IN ({placeholders})")
                    values.extend(value)
                else:
                    conditions.append(f"`{field}` = %s")
                    values.append(value)
        
        where_clause = " AND ".join(conditions)
        
        # Get data with limit for safety
        query = f"""
            SELECT {','.join([f'`{field}`' for field in fields])}
            FROM `tabContact`
            WHERE {where_clause}
            ORDER BY modified DESC
            LIMIT 10000
        """
        
        contacts = frappe.db.sql(query, values, as_dict=True)
        
        if format.lower() == "csv":
            # Generate CSV
            output = io.StringIO()
            if contacts:
                writer = csv.DictWriter(output, fieldnames=fields)
                writer.writeheader()
                writer.writerows(contacts)
            
            csv_content = output.getvalue()
            encoded_content = base64.b64encode(csv_content.encode()).decode()
            
            return {
                "success": True,
                "data": {
                    "content": encoded_content,
                    "filename": f"contacts_export_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    "format": "csv",
                    "total_records": len(contacts)
                }
            }
        
        else:
            # Return JSON data for other formats
            return {
                "success": True,
                "data": {
                    "contacts": contacts,
                    "total_records": len(contacts),
                    "format": "json"
                }
            }
            
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


# ============ UTILITY FUNCTIONS ============

def parse_csv_content(csv_content: str) -> List[Dict[str, Any]]:
    """Parse CSV content into list of dictionaries"""
    csv_file = io.StringIO(csv_content)
    reader = csv.DictReader(csv_file)
    return [row for row in reader]


def validate_bulk_contact_data(data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Validate bulk contact data"""
    validation_results = {
        "valid_count": 0,
        "invalid_count": 0,
        "valid_data": [],
        "errors": []
    }
    
    for idx, row in enumerate(data):
        row_errors = []
        
        # Clean empty values
        cleaned_row = {k: v for k, v in row.items() if v and str(v).strip()}
        
        # Basic validations
        if not any([cleaned_row.get("email_id"), cleaned_row.get("mobile_no"), cleaned_row.get("instagram")]):
            row_errors.append("At least one contact method (email_id, mobile_no, or instagram) is required")
        
        # Phone validation
        if cleaned_row.get("mobile_no"):
            import re
            mobile = str(cleaned_row["mobile_no"]).strip()
            mobile_pattern = r'^(\+91[-.\s]?)?[6-9]\d{9}$'
            clean_mobile = re.sub(r'[-.\s]', '', mobile)
            if not re.match(mobile_pattern, clean_mobile):
                row_errors.append("Invalid mobile number format")
        
        # GSTIN validation
        if cleaned_row.get("gstin"):
            import re
            gstin = str(cleaned_row["gstin"]).strip().upper()
            gstin_pattern = r'^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$'
            if not re.match(gstin_pattern, gstin):
                row_errors.append("Invalid GSTIN format")
            else:
                cleaned_row["gstin"] = gstin
        
        # Employee specific validations
        if cleaned_row.get("contact_type") == "Employee":
            if not cleaned_row.get("employee_code"):
                row_errors.append("Employee Code is required for Employee contacts")
        
        # Vendor specific validations
        if cleaned_row.get("contact_type") == "Vendor":
            if not cleaned_row.get("vendor_type"):
                row_errors.append("Vendor Type is required for Vendor contacts")
        
        if row_errors:
            validation_results["invalid_count"] += 1
            validation_results["errors"].append({
                "row": idx + 2,  # +2 for header and 0-index
                "errors": row_errors,
                "data": row
            })
        else:
            validation_results["valid_count"] += 1
            validation_results["valid_data"].append(cleaned_row)
    
    return validation_results


@frappe.whitelist()
def get_bulk_operation_status(operation_id: str) -> Dict[str, Any]:
    """
    Get status of a bulk operation (for future async operations)
    
    Args:
        operation_id: ID of the bulk operation
        
    Returns:
        Operation status and progress
    """
    # Placeholder for future async bulk operations
    return {
        "success": True,
        "data": {
            "operation_id": operation_id,
            "status": "completed",
            "message": "Bulk operations are currently synchronous"
        }
    }


@frappe.whitelist()
def get_bulk_import_template() -> Dict[str, Any]:
    """
    Get CSV template for bulk contact import
    
    Returns:
        CSV template with headers and sample data
    """
    try:
        # Define template headers
        headers = [
            "first_name", "last_name", "email_id", "mobile_no",
            "contact_type", "contact_category", "city", "state", "country",
            "pincode", "gstin", "employee_code", "vendor_type",
            "designation", "company_name", "dob", "date_of_joining",
            "instagram", "notes"
        ]
        
        # Sample data
        sample_data = [
            {
                "first_name": "John",
                "last_name": "Doe",
                "email_id": "john.doe@example.com",
                "mobile_no": "9876543210",
                "contact_type": "Customer",
                "contact_category": "Individual",
                "city": "Mumbai",
                "state": "Maharashtra",
                "country": "India",
                "pincode": "400001",
                "designation": "Manager",
                "company_name": "ABC Corp"
            },
            {
                "first_name": "Jane",
                "last_name": "Smith",
                "email_id": "jane.smith@company.com",
                "mobile_no": "9876543211",
                "contact_type": "Employee",
                "employee_code": "EMP001",
                "date_of_joining": "2024-01-15",
                "city": "Delhi",
                "state": "Delhi"
            }
        ]
        
        # Generate CSV
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=headers)
        writer.writeheader()
        writer.writerows(sample_data)
        
        csv_content = output.getvalue()
        encoded_content = base64.b64encode(csv_content.encode()).decode()
        
        return {
            "success": True,
            "data": {
                "content": encoded_content,
                "filename": "contact_import_template.csv",
                "headers": headers,
                "sample_count": len(sample_data)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }