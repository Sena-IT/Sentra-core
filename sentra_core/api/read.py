import frappe
from frappe import _
from typing import Dict, List, Optional, Any
import json
import re

@frappe.whitelist()
def get_list(
    doctype: str,
    filters: Optional[Dict[str, Any]] = None,
    fields: Optional[List[str]] = None,
    order_by: str = "modified desc",
    page: int = 1,
    page_size: int = 20,
    view: Optional[str] = None
) -> Dict[str, Any]:
    """
    Generic API to get list of documents for any DocType with filtering, sorting, and pagination
    
    Args:
        doctype: The DocType to query
        filters: Field filters (merged with view filters if view is specified)
        fields: Fields to return (uses view fields if not specified and view is provided)
        order_by: Sort order (uses view sorting if not specified and view is provided)
        page: Page number
        page_size: Items per page (uses view page_size if not specified and view is provided)
        view: Name of saved view to load configuration from
        
    Returns:
        Paginated list of documents
    """
    try:
        # Check permissions
        if not frappe.has_permission(doctype, "read"):
            frappe.throw(_("You don't have permission to access {0}").format(doctype))
        
        # Load view configuration if view is specified
        view_info = None
        if view:
            view_result = get_list_view(view, doctype)
            if view_result["success"]:
                view_config = view_result["data"]
                view_info = {
                    "view_name": view_config["view_name"],
                    "view_id": view_config["view_id"],
                    "is_owner": view_config["is_owner"],
                    "is_public": view_config["is_public"]
                }
                
                # Use view configuration as defaults (can be overridden by explicit parameters)
                if filters is None and view_config.get("filters"):
                    filters = view_config["filters"]
                elif filters and view_config.get("filters"):
                    # Merge view filters with provided filters (provided filters take precedence)
                    merged_filters = view_config["filters"].copy()
                    merged_filters.update(filters)
                    filters = merged_filters
                
                if fields is None and view_config.get("fields"):
                    fields = view_config["fields"]
                
                if order_by == "modified desc" and view_config.get("sorts"):
                    # Build order_by from view sorts
                    sort_parts = []
                    for sort in view_config["sorts"]:
                        direction = sort.get("direction", "asc")
                        field = sort.get("field", "modified")
                        sort_parts.append(f"{field} {direction}")
                    if sort_parts:
                        order_by = ", ".join(sort_parts)
                
                if page_size == 20 and view_config.get("page_size"):
                    page_size = view_config["page_size"]
            else:
                # View not found, but continue with regular processing
                pass
        
        # Parse parameters if they're strings
        if isinstance(filters, str):
            filters = json.loads(filters) if filters else {}
        if isinstance(fields, str):
            fields = json.loads(fields) if fields else None
            
        # Get metadata
        meta = frappe.get_meta(doctype)
        
        # Build sets of field types for validation
        table_fields = set()
        all_valid_fields = set()
        
        # Get all valid fields from meta
        for field in meta.fields:
            all_valid_fields.add(field.fieldname)
            if field.fieldtype in ["Table", "Table MultiSelect"]:
                table_fields.add(field.fieldname)
        
        # Add standard fields
        standard_fields = ["name", "owner", "creation", "modified", "modified_by", "docstatus", "idx"]
        all_valid_fields.update(standard_fields)
        
        # System fields that exist but may cause issues in queries
        system_fields = ["_comments", "_liked_by", "_assign", "_user_tags"]
        # Add system fields to valid fields list (they exist but we'll filter them out)
        all_valid_fields.update(system_fields)
        
        # Default fields if not specified
        if not fields:
            # Get fields marked for list view
            default_fields = ["name"]
            for field in meta.fields:
                if field.in_list_view and field.fieldtype not in ["Table", "Table MultiSelect"]:
                    default_fields.append(field.fieldname)
            # Add standard fields
            default_fields.extend(["modified", "creation"])
            # Remove duplicates while preserving order
            seen = set()
            fields = [f for f in default_fields if not (f in seen or seen.add(f))]
        else:
            # Filter and validate fields
            valid_fields = []
            invalid_fields = []
            
            for f in fields:
                if f not in all_valid_fields:
                    invalid_fields.append(f)
                elif f in table_fields:
                    continue  # Skip table fields silently
                elif f in system_fields:
                    continue  # Skip system fields silently
                else:
                    valid_fields.append(f)
            
            # If there are invalid fields, throw an error
            if invalid_fields:
                frappe.throw(f"Invalid fields requested: {', '.join(invalid_fields)}")
            
            # Remove duplicates while preserving order
            seen = set()
            fields = [f for f in valid_fields if not (f in seen or seen.add(f))]
            
            # Ensure we have at least one field
            if not fields:
                fields = ["name"]
                if meta.title_field:
                    fields.append(meta.title_field)
            
            # Ensure order_by field is included if it's a simple field reference
            if order_by:
                # Extract field name from order_by (e.g., "modified desc" -> "modified")
                order_field = order_by.split()[0].strip()
                # Remove any table prefix (e.g., "tabContact.modified" -> "modified")
                if "." in order_field:
                    order_field = order_field.split(".")[-1]
                
                # Add to fields if it's a valid field and not already included
                if order_field in all_valid_fields and order_field not in fields and order_field not in table_fields and order_field not in system_fields:
                    fields.append(order_field)
            
        # Build filters for Frappe API
        api_filters = filters.copy() if filters else {}
        
        # Handle search text
        or_filters = []
        
        
        # Get total count
        count_filters = api_filters.copy()
        if or_filters:
            total_count = len(frappe.get_all(doctype,
                filters=count_filters,
                or_filters=or_filters,
                pluck="name"
            ))
        else:
            total_count = frappe.db.count(doctype, filters=count_filters)
        
        # Get paginated results
        offset = (page - 1) * page_size
        
        try:
            # Clean order_by to prevent SQL injection
            if order_by:
                # Basic validation - only allow field names, direction, and basic punctuation
                order_parts = order_by.split(',')
                cleaned_parts = []
                for part in order_parts:
                    part = part.strip()
                    # Replace non-breaking spaces with regular spaces
                    part = part.replace('\xa0', ' ')
                    # Check for valid pattern: field_name [asc|desc]
                    if not re.match(r'^[a-zA-Z0-9_`]+(\s+(asc|desc))?$', part, re.IGNORECASE):
                        frappe.throw(f"Invalid order_by format: {part}")
                    cleaned_parts.append(part)
                order_by = ', '.join(cleaned_parts)
            
            if or_filters:
                documents = frappe.get_all(doctype,
                    filters=api_filters,
                    or_filters=or_filters,
                    fields=fields,
                    order_by=order_by,
                    start=offset,
                    page_length=page_size
                )
            else:
                documents = frappe.get_all(doctype,
                    filters=api_filters,
                    fields=fields,
                    order_by=order_by,
                    start=offset,
                    page_length=page_size
                )
        except Exception as query_error:
            # Log the actual query error for debugging
            import traceback
            frappe.log_error(f"Query Error: {str(query_error)}\nDocType: {doctype}\nFields: {fields}\nFilters: {api_filters}", f"{doctype} Query Error")
            frappe.log_error(traceback.format_exc(), f"{doctype} Query Traceback")
            
            # Check if it's a SQL error
            if "Illegal SQL Query" in str(query_error):
                # Try to identify the problematic field
                problematic_fields = []
                for field in fields:
                    try:
                        frappe.get_all(doctype, fields=[field], limit=1)
                    except:
                        problematic_fields.append(field)
                
                if problematic_fields:
                    return {
                        "success": False,
                        "message": f"Invalid fields in request: {', '.join(problematic_fields)}. These fields cannot be fetched in list views."
                    }
            
            raise  # Re-raise the error to be caught by outer exception handler
        
        result = {
            "success": True,
            "data": {
                "documents": documents,
                "pagination": {
                    "total": total_count,
                    "page": page,
                    "page_size": page_size,
                    "total_pages": (total_count + page_size - 1) // page_size
                }
            }
        }
        
        # Add view info if view was used
        if view_info:
            result["view_info"] = view_info
        
        return result
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        frappe.log_error(error_trace, f"{doctype} List Error")
        
        # Log the fields that were requested for debugging
        frappe.log_error(f"DocType: {doctype}\nRequested fields: {fields}\nFiltered fields: {fields if 'fields' in locals() else 'Not yet filtered'}", f"{doctype} List Fields Debug")
        
        # If it's an SQL error, provide more helpful message
        error_message = str(e)
        if "Illegal SQL Query" in error_message or "Unknown column" in error_message:
            return {
                "success": False,
                "message": f"Invalid field in request. Please check that all requested fields exist in {doctype} and are not child tables."
            }
        
        return {
            "success": False,
            "message": error_message
        }


@frappe.whitelist()
def get_document_with_linked_data(
    doctype: str,
    name: str,
    include_communications: bool = True,
    include_links: bool = True
) -> Dict[str, Any]:
    """
    Get a document with its linked documents and communications
    
    Args:
        doctype: The DocType to fetch
        name: Document name/ID
        include_communications: Whether to include communications
        include_links: Whether to include linked documents
        
    Returns:
        Document data with linked information
    """
    try:
        # Check permissions
        if not frappe.has_permission(doctype, "read", doc=name):
            frappe.throw(_("You don't have permission to access this document"))
        
        # Get the document
        doc = frappe.get_doc(doctype, name)
        doc_dict = doc.as_dict()
        
        # Add linked documents if requested
        if include_links:
            doc_dict["linked_documents"] = get_linked_documents(doctype, name)
        
        # Add communications if requested
        if include_communications:
            doc_dict["recent_communications"] = get_communications(doctype, name)
        
        return {
            "success": True,
            "data": doc_dict
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


def get_linked_documents(doctype: str, name: str) -> List[Dict[str, Any]]:
    """
    Get all documents linked to a specific document
    
    Args:
        doctype: The DocType of the document
        name: The name of the document
        
    Returns:
        List of linked documents
    """
    linked = []
    
    # Get Dynamic Links
    dynamic_links = frappe.get_all("Dynamic Link", 
        filters={
            "link_doctype": doctype,
            "link_name": name
        },
        fields=["parent", "parenttype", "link_title"]
    )
    
    for link in dynamic_links:
        # Try to get title/name of linked document
        try:
            meta = frappe.get_meta(link.parenttype)
            title_field = meta.title_field or "name"
            
            doc_data = frappe.db.get_value(
                link.parenttype, 
                link.parent, 
                [title_field, "name"], 
                as_dict=True
            )
            
            title = doc_data.get(title_field) or link.parent
        except:
            title = link.parent
        
        linked.append({
            "doctype": link.parenttype,
            "name": link.parent,
            "title": title,
            "link_type": "Dynamic Link"
        })
    
    # Get Links from Link fields pointing to this document
    # This requires checking all DocTypes that have Link fields pointing to our DocType
    try:
        # Get all DocTypes that have a Link field to our DocType
        link_fields = frappe.get_all("DocField",
            filters={
                "fieldtype": "Link",
                "options": doctype
            },
            fields=["parent", "fieldname"]
        )
        
        for field in link_fields:
            # Get documents where this link field points to our document
            linked_docs = frappe.get_all(field.parent,
                filters={field.fieldname: name},
                limit=10  # Limit to prevent too many results
            )
            
            for linked_doc in linked_docs:
                try:
                    meta = frappe.get_meta(field.parent)
                    title_field = meta.title_field or "name"
                    
                    doc_data = frappe.db.get_value(
                        field.parent,
                        linked_doc.name,
                        [title_field, "name"],
                        as_dict=True
                    )
                    
                    title = doc_data.get(title_field) or linked_doc.name
                except:
                    title = linked_doc.name
                
                linked.append({
                    "doctype": field.parent,
                    "name": linked_doc.name,
                    "title": title,
                    "link_type": f"Link Field ({field.fieldname})"
                })
    except:
        pass  # Ignore errors in getting link fields
    
    return linked


def get_communications(doctype: str, name: str, limit: int = 10) -> List[Dict[str, Any]]:
    """
    Get recent communications for a document
    
    Args:
        doctype: The DocType
        name: Document name
        limit: Maximum number of communications to return
        
    Returns:
        List of recent communications
    """
    communications = frappe.get_all("Communication",
        filters={
            "reference_doctype": doctype,
            "reference_name": name
        },
        fields=[
            "name", "subject", "content", "communication_type",
            "sent_or_received", "communication_date", "sender", "recipients"
        ],
        order_by="communication_date desc",
        limit=limit
    )
    
    return communications


@frappe.whitelist()
def save_list_view(
    doctype: str,
    view_name: str,
    filters: Optional[Dict[str, Any]] = None,
    sorts: Optional[List[Dict[str, str]]] = None,
    columns: Optional[List[Dict[str, Any]]] = None,
    fields: Optional[List[str]] = None,
    page_size: int = 20,
    is_default: bool = False,
    is_public: bool = False,
    view_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Save a custom list view configuration for any DocType
    
    Args:
        doctype: The DocType this view is for
        view_name: Name of the saved view
        filters: Filter conditions to apply
        sorts: Sort conditions (list of {field, direction})
        columns: Column display configuration for UI
        fields: Fields to fetch from database
        page_size: Number of items per page
        is_default: Make this the default view for the user
        is_public: Share this view with all users
        view_id: ID of existing view to update
        
    Returns:
        Saved view configuration
    """
    try:
        # Parse parameters if strings
        if isinstance(filters, str):
            filters = json.loads(filters) if filters else {}
        if isinstance(sorts, str):
            sorts = json.loads(sorts) if sorts else []
        if isinstance(columns, str):
            columns = json.loads(columns) if columns else []
        if isinstance(fields, str):
            fields = json.loads(fields) if fields else []
        
        if view_id:
            # Update existing view
            view = frappe.get_doc("CRM View Settings", view_id)
            
            # Check permissions
            if view.owner != frappe.session.user and not frappe.has_permission("CRM View Settings", "write", doc=view):
                frappe.throw(_("You don't have permission to edit this view"))
        else:
            # Create new view with meaningful name
            # Generate a unique name combining doctype, view_name and user
            base_name = f"{doctype}-{view_name}".replace(" ", "-").lower()
            
            # Check if view with this name already exists for this user
            existing_view = frappe.db.exists("CRM View Settings", {
                "dt": doctype,
                "label": view_name,
                "user": frappe.session.user
            })
            
            if existing_view:
                # Update existing view instead of creating new one
                view = frappe.get_doc("CRM View Settings", existing_view)
            else:
                # Create new view
                view = frappe.new_doc("CRM View Settings")
                view.name = base_name
        
        # If setting as default, unset other defaults for this user and doctype
        if is_default:
            frappe.db.set_value("CRM View Settings", {
                "user": frappe.session.user,
                "dt": doctype,
                "is_default": 1
            }, "is_default", 0)
        
        # Update view fields based on actual CRM View Settings schema
        view.update({
            "label": view_name,  # Changed from view_name to label
            "dt": doctype,
            "filters": json.dumps(filters) if filters else "{}",
            "order_by": json.dumps([{"field": sorts[0].get("field"), "direction": sorts[0].get("direction", "asc")}]) if sorts and len(sorts) > 0 else "[]",
            "columns": json.dumps(columns) if columns else "[]",
            "rows": json.dumps(fields) if fields else "[]",
            "is_default": is_default,
            "public": is_public,  # Changed from is_public to public
            "user": frappe.session.user  # Set the user field
        })
        
        view.save()
        
        return {
            "success": True,
            "message": _("View saved successfully"),
            "data": {
                "view_id": view.name,
                "view_name": view.label,  # Changed from view_name to label
                "is_default": view.is_default,
                "is_public": view.public  # Changed from is_public to public
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_list_views(doctype: str) -> Dict[str, Any]:
    """
    Get all saved list views for a DocType accessible to current user
    
    Args:
        doctype: The DocType to get views for
        
    Returns:
        List of saved views
    """
    try:
        # Get all views for the doctype (user's own + public ones)
        views = frappe.get_all("CRM View Settings",
            filters={
                "dt": doctype,
            },
            fields=[
                "name", "label", "user", "is_default", 
                "public", "creation", "modified"
            ],
            order_by="is_default desc, modified desc"
        )
        
        # Filter to show only user's own views + public views from others
        filtered_views = []
        for view in views:
            if view["user"] == frappe.session.user or view["public"] == 1:
                # Add backward compatibility fields
                view["is_owner"] = view["user"] == frappe.session.user
                view["view_name"] = view["label"]
                view["owner"] = view["user"]
                view["is_public"] = view["public"]
                filtered_views.append(view)
        
        views = filtered_views
        
        return {
            "success": True,
            "data": views
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_list_view(view_name: str, doctype: str = None) -> Dict[str, Any]:
    """
    Get details of a specific saved list view
    
    Args:
        view_name: Name of the saved view
        doctype: DocType (optional, helps narrow search if multiple doctypes have same view name)
        
    Returns:
        View configuration details
    """
    try:
        # Search for the view by label (view_name)
        # Handle both cases: views with proper labels and legacy views
        search_filters = []
        
        if doctype:
            base_filter = {"dt": doctype}
        else:
            base_filter = {}
        
        # Try to find by label first
        label_filters = base_filter.copy()
        label_filters.update({"label": view_name, "user": frappe.session.user})
        view_name_exists = frappe.db.exists("CRM View Settings", label_filters)
        
        if not view_name_exists:
            # Try public views with label
            label_filters = base_filter.copy()
            label_filters.update({"label": view_name, "public": 1})
            view_name_exists = frappe.db.exists("CRM View Settings", label_filters)
        
        if not view_name_exists:
            # Fallback: search by generated name pattern (for backward compatibility)
            if doctype:
                generated_name = f"{doctype.lower()}-{view_name.replace(' ', '-').lower()}"
                name_filters = {"name": generated_name}
                view_name_exists = frappe.db.exists("CRM View Settings", name_filters)
        
        if not view_name_exists:
            frappe.throw(_("View '{0}' not found").format(view_name))
        
        view = frappe.get_doc("CRM View Settings", view_name_exists)
        
        # Check permissions
        if view.user != frappe.session.user and not view.public:
            frappe.throw(_("You don't have permission to access this view"))
        
        # Parse JSON fields
        filters = json.loads(view.filters or "{}")
        columns = json.loads(view.columns or "[]")
        fields = json.loads(view.rows or "[]")
        
        # Build sorts array from order_by field
        sorts = []
        if view.order_by:
            try:
                order_by_data = json.loads(view.order_by)
                if isinstance(order_by_data, list) and len(order_by_data) > 0:
                    sorts = order_by_data
            except:
                # Fallback if order_by is not JSON
                pass
        
        return {
            "success": True,
            "data": {
                "view_id": view.name,
                "view_name": view.label,  # Changed from view_name to label
                "doctype": view.dt,
                "filters": filters,
                "sorts": sorts,
                "columns": columns,
                "fields": fields,
                "page_size": 20,  # Default since load_limit doesn't exist
                "is_default": view.is_default,
                "is_public": view.public,  # Changed from is_public to public
                "is_owner": view.user == frappe.session.user,  # Changed from owner to user
                "owner": view.user,  # Changed from owner to user
                "modified": view.modified
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def delete_list_view(view_name: str, doctype: str = None) -> Dict[str, Any]:
    """
    Delete a saved list view
    
    Args:
        view_name: Name of the view to delete
        doctype: DocType (optional, helps narrow search)
        
    Returns:
        Deletion status
    """
    try:
        # Search for the view by label (view_name) - only user's own views can be deleted
        filters = {
            "label": view_name,
            "user": frappe.session.user
        }
        if doctype:
            filters["dt"] = doctype
        
        view_exists = frappe.db.exists("CRM View Settings", filters)
        
        if not view_exists:
            frappe.throw(_("View '{0}' not found or you don't have permission to delete it").format(view_name))
        
        view = frappe.get_doc("CRM View Settings", view_exists)
        
        # Double check permissions (should already be filtered above)
        if view.user != frappe.session.user:
            frappe.throw(_("You can only delete your own views"))
        
        view.delete()
        
        return {
            "success": True,
            "message": _("View deleted successfully")
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


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
            "Geolocation",
            "Table",  # Child tables cannot be shown in list views
            "Table MultiSelect"
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