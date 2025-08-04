import frappe
from frappe import _
from typing import Dict, List, Optional, Any
import json

@frappe.whitelist()
def get_contact_with_details(contact_name: str) -> Dict[str, Any]:
    """
    Get contact with enhanced details including calculated fields
    
    Args:
        contact_name: Contact ID/name
        
    Returns:
        Enhanced contact data with computed fields
    """
    try:
        contact = frappe.get_doc("Contact", contact_name)
        
        # Use the enhanced get_formatted_data method
        if hasattr(contact, 'get_formatted_data'):
            data = contact.get_formatted_data()
        else:
            data = contact.as_dict()
        
        # Add recent activity
        data['recent_communications'] = get_recent_communications(contact_name)
        data['linked_documents'] = get_linked_documents(contact_name)
        
        return {
            "success": True,
            "data": data
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
        
        # Get all linked documents
        linked_docs = []
        
        # Check Dynamic Links
        dynamic_links = frappe.get_all("Dynamic Link", 
            filters={
                "link_doctype": "Contact",
                "link_name": contact_name
            },
            fields=["parent", "parenttype"]
        )
        
        for link in dynamic_links:
            linked_docs.append({
                "doctype": link.parenttype,
                "name": link.parent,
                "type": "Dynamic Link"
            })
        
        # Check if this contact is someone's manager
        managed_contacts = frappe.get_all("Contact",
            filters={"manager": contact_name, "name": ["!=", contact_name]},
            fields=["name", "full_name"]
        )
        
        for managed in managed_contacts:
            linked_docs.append({
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
            linked_docs.append({
                "doctype": "Communication",
                "name": comm.name,
                "title": comm.subject,
                "type": "Communication History"
            })
        
        can_delete = len(linked_docs) == 0 or all(doc["type"] == "Communication History" for doc in linked_docs)
        
        return {
            "success": True,
            "data": {
                "can_delete": can_delete,
                "linked_documents": linked_docs,
                "message": _("Contact can be safely deleted") if can_delete else _("Contact has dependencies that must be resolved first")
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


def get_recent_communications(contact_name: str) -> List[Dict[str, Any]]:
    """Get recent communications for a contact"""
    communications = frappe.get_all("Communication",
        filters={
            "reference_doctype": "Contact",
            "reference_name": contact_name
        },
        fields=[
            "name", "subject", "content", "communication_type",
            "sent_or_received", "communication_date", "sender", "recipients"
        ],
        order_by="communication_date desc",
        limit=10
    )
    
    return communications


def get_linked_documents(contact_name: str) -> List[Dict[str, Any]]:
    """Get documents linked to this contact"""
    linked = []
    
    # Get Dynamic Links with additional info
    dynamic_links = frappe.get_all("Dynamic Link", 
        filters={
            "link_doctype": "Contact",
            "link_name": contact_name
        },
        fields=["parent", "parenttype", "link_title"]
    )
    
    for link in dynamic_links:
        # Try to get title/name of linked document
        try:
            doc_data = frappe.db.get_value(link.parenttype, link.parent, 
                ["name", "title", "subject", "customer_name", "supplier_name"], as_dict=True)
            
            title = (doc_data.get("title") or 
                    doc_data.get("subject") or 
                    doc_data.get("customer_name") or 
                    doc_data.get("supplier_name") or 
                    link.parent)
        except:
            title = link.parent
        
        linked.append({
            "doctype": link.parenttype,
            "name": link.parent,
            "title": title
        })
    
    return linked


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