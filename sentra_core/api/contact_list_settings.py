import frappe
from frappe import _
from typing import Dict, List, Optional, Any
import json
from pypika import Criterion


@frappe.whitelist()
def save_list_view(
    view_name: str,
    filters: Optional[Dict[str, Any]] = None,
    sorts: Optional[List[Dict[str, str]]] = None,
    columns: Optional[List[Dict[str, Any]]] = None,
    rows: Optional[List[str]] = None,
    page_size: int = 20,
    is_default: bool = False,
    is_public: bool = False,
    view_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save a custom list view configuration for contacts
    
    Args:
        view_name: Name of the saved view (e.g., "Active Mumbai Employees")
        filters: Filter conditions to apply (e.g., {"contact_type": "Employee", "city": "Mumbai"})
        sorts: Sort conditions (list of {field, direction}) (e.g., [{"field": "name", "direction": "asc"}])
        columns: Column display configuration for list view - how columns appear in UI
                 (e.g., [{"label": "Full Name", "fieldname": "full_name", "width": "10rem"}])
        rows: Fields to fetch from database - which fields to retrieve in the query
              (e.g., ["name", "full_name", "email_id", "mobile_no"])
        page_size: Number of items per page (default: 20)
        is_default: Make this the default view for the user - automatically loads when they visit contacts
        is_public: Share this view with all users in the system (false = private to creator)
        view_id: ID of existing view to update (optional)
        
    Returns:
        Saved view configuration
        
    Note:
        - columns: Defines how fields are displayed in the UI (label, width, formatting)
        - rows: Defines which fields are fetched from the database
        - is_default: Only one view can be default per user. Setting a new default unsets the previous one
        - is_public: Public views are visible to all users but can only be edited by the creator
    """
    try:
        # Parse parameters if strings
        if isinstance(filters, str):
            filters = json.loads(filters) if filters else {}
        if isinstance(sorts, str):
            sorts = json.loads(sorts) if sorts else []
        if isinstance(columns, str):
            columns = json.loads(columns) if columns else []
        if isinstance(rows, str):
            rows = json.loads(rows) if rows else []
            
        # Check if updating existing view
        if view_id:
            doc = frappe.get_doc("CRM View Settings", view_id)
            # Check permissions
            if doc.user != frappe.session.user and not frappe.has_permission("CRM View Settings", "write", doc):
                frappe.throw(_("You don't have permission to update this view"))
        else:
            # Check if view already exists for this user
            existing = frappe.db.get_value("CRM View Settings", {
                "label": view_name,
                "dt": "Contact",
                "user": frappe.session.user
            })
            
            if existing:
                doc = frappe.get_doc("CRM View Settings", existing)
            else:
                doc = frappe.new_doc("CRM View Settings")
                doc.label = view_name
                doc.dt = "Contact"
                doc.user = frappe.session.user if not is_public else ""
                
        # Update view configuration
        doc.filters = json.dumps(filters) if filters else "{}"
        
        # Convert sorts to order_by format
        order_by_parts = []
        for sort in sorts:
            if isinstance(sort, dict):
                field = sort.get("field")
                direction = sort.get("direction", "asc").lower()
                if field:
                    order_by_parts.append(f"{field} {direction}")
        doc.order_by = json.dumps(order_by_parts) if order_by_parts else '["modified desc"]'
        
        doc.columns = json.dumps(columns) if columns else "[]"
        doc.rows = json.dumps(rows) if rows else "[]"
        doc.public = 1 if is_public else 0
        doc.type = "list"
        
        # Handle default view
        if is_default:
            # Remove default flag from other views for this user and doctype
            other_views = frappe.get_all("CRM View Settings", 
                filters={
                    "dt": "Contact",
                    "user": frappe.session.user,
                    "name": ["!=", doc.name if doc.name else ""]
                },
                fields=["name"]
            )
            
            for view in other_views:
                frappe.db.set_value("CRM View Settings", view.name, "is_default", 0)
                
            doc.is_default = 1
        else:
            doc.is_default = 0
            
        doc.save()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("List view saved successfully"),
            "data": {
                "name": doc.name,
                "view_name": doc.label,
                "filters": json.loads(doc.filters),
                "sorts": sorts,
                "columns": json.loads(doc.columns),
                "rows": json.loads(doc.rows),
                "page_size": page_size,
                "is_default": doc.is_default,
                "is_public": doc.public
            }
        }
    except Exception as e:
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_list_views() -> Dict[str, Any]:
    """
    Get all saved list views for contacts (user's own + public views)
    
    Returns:
        List of saved views
    """
    try:
        View = frappe.qb.DocType("CRM View Settings")
        views = (
            frappe.qb.from_(View)
            .select("*")
            .where(View.dt == "Contact")
            .where(Criterion.any([View.user == "", View.user == frappe.session.user]))
            .orderby(View.is_default, order=frappe.qb.desc)
            .orderby(View.modified, order=frappe.qb.desc)
            .run(as_dict=True)
        )
        
        # Parse JSON fields and format response
        formatted_views = []
        for view in views:
            try:
                filters = json.loads(view.get('filters', '{}'))
                columns = json.loads(view.get('columns', '[]'))
                rows = json.loads(view.get('rows', '[]'))
                order_by = json.loads(view.get('order_by', '[]'))
                
                # Convert order_by back to sorts format
                sorts = []
                for order in order_by:
                    if isinstance(order, str):
                        parts = order.strip().split()
                        if len(parts) >= 1:
                            field = parts[0]
                            direction = parts[1] if len(parts) > 1 else "asc"
                            sorts.append({"field": field, "direction": direction})
                
                formatted_views.append({
                    "name": view['name'],
                    "view_name": view['label'],
                    "filters": filters,
                    "sorts": sorts,
                    "columns": columns,
                    "rows": rows,
                    "is_default": view.get('is_default', 0),
                    "is_public": view.get('public', 0),
                    "is_mine": view['user'] == frappe.session.user,
                    "owner": view['user'] or "Public",
                    "modified": str(view['modified'])
                })
            except Exception as e:
                frappe.log_error(f"Error parsing view {view.get('name')}: {str(e)}")
                continue
            
        return {
            "success": True,
            "data": formatted_views
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_list_view(view_id: str) -> Dict[str, Any]:
    """
    Get a specific saved list view configuration
    
    Args:
        view_id: ID of the saved view
        
    Returns:
        View configuration
    """
    try:
        view = frappe.get_doc("CRM View Settings", view_id)
        
        # Check permissions
        if view.user and view.user != frappe.session.user and not view.public:
            frappe.throw(_("You don't have permission to access this view"))
        
        # Parse JSON fields
        filters = json.loads(view.get('filters', '{}'))
        columns = json.loads(view.get('columns', '[]'))
        rows = json.loads(view.get('rows', '[]'))
        order_by = json.loads(view.get('order_by', '[]'))
        
        # Convert order_by back to sorts format
        sorts = []
        for order in order_by:
            if isinstance(order, str):
                parts = order.strip().split()
                if len(parts) >= 1:
                    field = parts[0]
                    direction = parts[1] if len(parts) > 1 else "asc"
                    sorts.append({"field": field, "direction": direction})
        
        return {
            "success": True,
            "data": {
                "name": view.name,
                "view_name": view.label,
                "filters": filters,
                "sorts": sorts,
                "columns": columns,
                "rows": rows,
                "is_default": view.is_default,
                "is_public": view.public,
                "is_mine": view.user == frappe.session.user
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def delete_list_view(view_id: str) -> Dict[str, Any]:
    """
    Delete a saved list view
    
    Args:
        view_id: ID of the view to delete
        
    Returns:
        Deletion status
    """
    try:
        # Get the view
        view = frappe.get_doc("CRM View Settings", view_id)
        
        # Check permissions
        if view.user != frappe.session.user:
            frappe.throw(_("You can only delete your own views"))
            
        view.delete()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _("List view deleted successfully")
        }
    except Exception as e:
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_contacts_with_view(
    view_id: Optional[str] = None,
    page: int = 1,
    page_size: Optional[int] = None,
    override_filters: Optional[Dict[str, Any]] = None,
    override_sorts: Optional[List[Dict[str, str]]] = None,
    search_text: Optional[str] = None
) -> Dict[str, Any]:
    """
    Get contacts list using a saved view or default settings
    
    Args:
        view_id: ID of saved view to apply
        page: Page number
        page_size: Items per page (overrides view setting)
        override_filters: Additional filters to apply on top of saved view
        override_sorts: Override the saved sorting
        search_text: Search text
        
    Returns:
        Paginated contact list with applied view settings
    """
    try:
        # Parse override parameters
        if isinstance(override_filters, str):
            override_filters = json.loads(override_filters) if override_filters else {}
        if isinstance(override_sorts, str):
            override_sorts = json.loads(override_sorts) if override_sorts else []
            
        # Initialize default values
        filters = {}
        sorts = []
        columns = []
        rows = []
        default_page_size = 20
        view_data = None
        
        # Load saved view if specified
        if view_id:
            view_result = get_list_view(view_id)
            if view_result["success"]:
                view_data = view_result["data"]
                filters = view_data.get("filters", {})
                sorts = view_data.get("sorts", [])
                columns = view_data.get("columns", [])
                rows = view_data.get("rows", [])
        else:
            # Try to load default view
            View = frappe.qb.DocType("CRM View Settings")
            default_view = (
                frappe.qb.from_(View)
                .select("*")
                .where(View.dt == "Contact")
                .where(View.user == frappe.session.user)
                .where(View.is_default == 1)
                .limit(1)
                .run(as_dict=True)
            )
            
            if default_view:
                view = default_view[0]
                filters = json.loads(view.get("filters", "{}"))
                order_by = json.loads(view.get("order_by", "[]"))
                columns = json.loads(view.get("columns", "[]"))
                rows = json.loads(view.get("rows", "[]"))
                
                # Convert order_by to sorts
                sorts = []
                for order in order_by:
                    if isinstance(order, str):
                        parts = order.strip().split()
                        if len(parts) >= 1:
                            field = parts[0]
                            direction = parts[1] if len(parts) > 1 else "asc"
                            sorts.append({"field": field, "direction": direction})
        
        # Apply override filters
        if override_filters:
            filters.update(override_filters)
            
        # Apply override sorts or use saved sorts
        if override_sorts:
            sorts = override_sorts
            
        # Convert sorts to order_by string
        order_by_parts = []
        for sort in sorts:
            if isinstance(sort, dict):
                field = sort.get("field")
                direction = sort.get("direction", "asc").upper()
                if field and direction in ["ASC", "DESC"]:
                    order_by_parts.append(f"`{field}` {direction}")
                    
        order_by = ", ".join(order_by_parts) if order_by_parts else "modified desc"
        
        # Use provided page_size or default
        if not page_size:
            page_size = default_page_size
            
        # Import and use the existing get_contacts function
        from sentra_core.api.contact import get_contacts
        
        # Determine fields to return
        fields = rows if rows else None
        
        # Call the existing API with view settings
        result = get_contacts(
            filters=filters,
            fields=fields,
            order_by=order_by,
            page=page,
            page_size=page_size,
            search_text=search_text
        )
        
        # Add view information to response
        if result.get("success"):
            result["data"]["applied_view"] = {
                "name": view_data.get("name") if view_data else None,
                "view_name": view_data.get("view_name") if view_data else None,
                "filters": filters,
                "sorts": sorts,
                "columns": columns,
                "rows": rows,
                "page_size": page_size
            }
            
        return result
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_default_list_columns() -> Dict[str, Any]:
    """
    Get available columns for contact list view
    
    Returns:
        List of available fields that can be shown in list view
    """
    try:
        # Use the generic doctype fields API
        from sentra_core.api.doctype_fields import get_list_fields
        
        return get_list_fields("Contact")
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }