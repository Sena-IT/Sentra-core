import frappe
from frappe import _
from typing import Dict, List, Optional, Any
import json

# Import generic functions from read.py
from sentra_core.api.read import get_linked_documents, get_communications


@frappe.whitelist()
def get_contact_detail(contact_name: str) -> Dict[str, Any]:
    """
    Get detailed information about a single contact with enhanced data
    
    Args:
        contact_name: Contact ID/name
        
    Returns:
        Complete contact information including linked data and computed fields
    """
    try:
        contact = frappe.get_doc("Contact", contact_name)
        contact_dict = contact.as_dict()
        
        # Add computed fields if available
        if hasattr(contact, 'get_formatted_data'):
            contact_dict = contact.get_formatted_data()
        
        # Add recent communications
        contact_dict['recent_communications'] = get_communications("Contact", contact_name)
        
        # Add linked documents
        contact_dict['linked_documents'] = get_linked_documents("Contact", contact_name)
        
        return {
            "success": True,
            "data": contact_dict
        }
    except frappe.DoesNotExistError:
        return {
            "success": False,
            "message": _("Contact {0} not found").format(contact_name)
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_contact_summary(contact_name: str) -> Dict[str, Any]:
    """
    Get contact summary for quick views/cards
    
    Args:
        contact_name: Contact ID/name
        
    Returns:
        Summarized contact data
    """
    try:
        fields = [
            "name", "full_name", "first_name", "last_name",
            "email_id", "mobile_no", "contact_type", "contact_category",
            "city", "state", "company_name", "designation", "image"
        ]
        
        contact_data = frappe.db.get_value("Contact", contact_name, fields, as_dict=True)
        
        if not contact_data:
            return {
                "success": False,
                "message": _("Contact not found")
            }
        
        # Add computed summary info
        contact = frappe.get_doc("Contact", contact_name)
        contact_data['age'] = contact.calculate_age() if hasattr(contact, 'calculate_age') else None
        contact_data['years_of_service'] = contact.calculate_years_of_service() if hasattr(contact, 'calculate_years_of_service') else None
        
        return {
            "success": True,
            "data": contact_data
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_contact_hierarchy(contact_name: str) -> Dict[str, Any]:
    """
    Get employee hierarchy (manager and reportees) for a contact
    
    Args:
        contact_name: Contact ID/name
        
    Returns:
        Hierarchy data with manager chain and direct reports
    """
    try:
        contact = frappe.get_doc("Contact", contact_name)
        
        if contact.contact_type != "Employee":
            return {
                "success": False,
                "message": _("Hierarchy is only available for Employee contacts")
            }
        
        # Get manager chain (upward)
        manager_chain = []
        current_manager = contact.manager
        seen_managers = set()
        
        while current_manager and current_manager not in seen_managers:
            seen_managers.add(current_manager)
            manager_data = frappe.db.get_value("Contact", current_manager, 
                ["name", "full_name", "designation", "manager"], as_dict=True)
            
            if manager_data:
                manager_chain.append(manager_data)
                current_manager = manager_data.manager
            else:
                break
        
        # Get direct reports (downward)
        direct_reports = frappe.get_all("Contact",
            filters={"manager": contact_name, "contact_type": "Employee"},
            fields=["name", "full_name", "designation", "employee_status"]
        )
        
        # Get team size (all reports including indirect)
        team_size = get_team_size(contact_name)
        
        return {
            "success": True,
            "data": {
                "contact": {
                    "name": contact.name,
                    "full_name": contact.full_name,
                    "designation": contact.designation,
                    "employee_code": contact.employee_code
                },
                "manager_chain": manager_chain,
                "direct_reports": direct_reports,
                "team_size": team_size
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def validate_contact_deletion(contact_name: str) -> Dict[str, Any]:
    """
    Check if contact can be safely deleted (dry-run validation)
    
    Args:
        contact_name: Contact ID/name
        
    Returns:
        Validation result with linked documents
    """
    try:
        contact = frappe.get_doc("Contact", contact_name)
        
        # Get all linked documents using generic function
        linked_docs = get_linked_documents("Contact", contact_name)
        
        # Convert to expected format
        formatted_linked_docs = []
        for doc in linked_docs:
            formatted_linked_docs.append({
                "doctype": doc["doctype"],
                "name": doc["name"],
                "title": doc.get("title", doc["name"]),
                "type": doc.get("link_type", "Link")
            })
        
        # Check if this contact is someone's manager
        managed_contacts = frappe.get_all("Contact",
            filters={"manager": contact_name, "name": ["!=", contact_name]},
            fields=["name", "full_name"]
        )
        
        for managed in managed_contacts:
            formatted_linked_docs.append({
                "doctype": "Contact",
                "name": managed.name,
                "title": managed.full_name,
                "type": "Manager Reference"
            })
        
        # Check communications
        communications = frappe.get_all("Communication",
            filters={"reference_doctype": "Contact", "reference_name": contact_name},
            fields=["name", "subject", "communication_date"],
            limit=5
        )
        
        for comm in communications:
            formatted_linked_docs.append({
                "doctype": "Communication",
                "name": comm.name,
                "title": comm.subject,
                "type": "Communication History"
            })
        
        can_delete = len(formatted_linked_docs) == 0 or all(doc["type"] == "Communication History" for doc in formatted_linked_docs)
        
        return {
            "success": True,
            "data": {
                "can_delete": can_delete,
                "linked_documents": formatted_linked_docs,
                "message": _("Contact can be safely deleted") if can_delete else _("Contact has dependencies that must be resolved first")
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


def get_team_size(manager_id: str, visited=None) -> int:
    """Recursively calculate team size including indirect reports"""
    if visited is None:
        visited = set()
    
    if manager_id in visited:
        return 0
    
    visited.add(manager_id)
    
    direct_reports = frappe.get_all("Contact",
        filters={"manager": manager_id, "contact_type": "Employee"},
        fields=["name"]
    )
    
    total_size = len(direct_reports)
    
    # Add indirect reports
    for report in direct_reports:
        total_size += get_team_size(report.name, visited)
    
    return total_size