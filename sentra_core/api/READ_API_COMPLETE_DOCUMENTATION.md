# Complete Read API Documentation
**File**: `sentra_core/api/read.py`

## Overview

The Read API provides a comprehensive set of functions for retrieving and managing data from any Frappe DocType. This API is designed to be generic, reusable, and feature-rich, supporting advanced filtering, pagination, field selection, sorting, and saved view management.

### Key Features
- **Universal DocType Support**: Works with any Frappe DocType (Contact, User, Lead, etc.)
- **Advanced Filtering**: Complex filter conditions with multiple operators
- **Field Validation**: Automatic validation of requested fields against DocType schema
- **Saved Views**: Create, manage, and use custom saved views with filters and configurations
- **Permission Aware**: Respects Frappe's built-in permission system
- **SQL Injection Protection**: Secure input validation and sanitization
- **Pagination Support**: Efficient pagination for large datasets

---

## API Functions

### 1. `get_list()` - Primary List Retrieval API

**Purpose**: Retrieve a paginated list of documents from any DocType with advanced filtering, sorting, and field selection.

**Endpoint**: `POST /api/method/sentra_core.api.read.get_list`

**Parameters**:
- `doctype` (string, **required**): The DocType to query (e.g., "Contact", "User", "Lead")
- `filters` (object, optional): Field-value pairs for filtering results
- `fields` (array, optional): Specific fields to return. If not specified, uses fields marked for list view
- `order_by` (string, optional): Sort order. Default: "modified desc"
- `page` (integer, optional): Page number for pagination. Default: 1
- `page_size` (integer, optional): Number of items per page. Default: 20
- `view` (string, optional): Name of saved view to load configuration from

**Filter Operators**:
```javascript
// Simple equality
"field": "value"

// Operators
"field": ["=", "value"]        // equals (default)
"field": ["!=", "value"]       // not equals
"field": [">", "value"]        // greater than
"field": ["<", "value"]        // less than
"field": [">=", "value"]       // greater than or equal
"field": ["<=", "value"]       // less than or equal
"field": ["like", "%pattern%"] // SQL LIKE
"field": ["in", ["val1", "val2"]] // IN list
"field": ["not in", ["val1", "val2"]] // NOT IN list
"field": ["is", "set"]         // is not null
"field": ["is", "not set"]     // is null
```

**Request Examples**:

```json
// Basic usage - get all contacts
{
    "doctype": "Contact"
}

// With filters
{
    "doctype": "Contact",
    "filters": {
        "city": "Mumbai",
        "contact_type": "Customer"
    }
}

// With specific fields
{
    "doctype": "Contact",
    "filters": {"status": "Active"},
    "fields": ["name", "full_name", "email_id", "mobile_no", "city"]
}

// With complex filters
{
    "doctype": "Contact",
    "filters": {
        "city": "Mumbai",
        "contact_type": ["in", ["Customer", "Vendor"]],
        "email_id": ["is", "set"],
        "modified": [">", "2024-01-01"]
    }
}

// With pagination and sorting
{
    "doctype": "Contact",
    "filters": {"contact_type": "Customer"},
    "order_by": "full_name asc",
    "page": 2,
    "page_size": 50
}

// Using a saved view
{
    "doctype": "Contact",
    "view": "Mumbai Customers"
}

// Using saved view with overrides
{
    "doctype": "Contact",
    "view": "Mumbai Customers",
    "page": 3,
    "filters": {"status": "Active"}
}
```

**Response Format**:
```json
{
    "success": true,
    "data": {
        "documents": [
            {
                "name": "CONT-001",
                "full_name": "John Doe",
                "email_id": "john@example.com",
                "mobile_no": "+1234567890",
                "city": "Mumbai",
                "modified": "2024-01-15 10:30:00"
            }
        ],
        "pagination": {
            "total": 150,
            "page": 1,
            "page_size": 20,
            "total_pages": 8
        }
    },
    "view_info": {  // Only present when using 'view' parameter
        "view_name": "Mumbai Customers",
        "view_id": "contact-mumbai-customers",
        "is_owner": true,
        "is_public": false
    }
}
```

---

### 2. `get_list_fields()` - Field Discovery API

**Purpose**: Get all available fields for a DocType that can be used in list views, including field metadata.

**Endpoint**: `POST /api/method/sentra_core.api.read.get_list_fields`

**Parameters**:
- `doctype` (string, **required**): The DocType to get fields for

**Request Example**:
```json
{
    "doctype": "Contact"
}
```

**Response Format**:
```json
{
    "success": true,
    "data": {
        "fields": [
            {
                "fieldname": "name",
                "label": "ID",
                "fieldtype": "Data",
                "in_standard_filter": true,
                "applicable_to": "all"
            },
            {
                "fieldname": "full_name", 
                "label": "Full Name",
                "fieldtype": "Data",
                "reqd": false,
                "in_list_view": true,
                "in_standard_filter": false,
                "in_global_search": true,
                "applicable_to": "all"
            },
            {
                "fieldname": "contact_type",
                "label": "Contact Type", 
                "fieldtype": "Select",
                "options": "Customer\nVendor\nEmployee",
                "applicable_to": "all"
            },
            {
                "fieldname": "employee_code",
                "label": "Employee Code",
                "fieldtype": "Data", 
                "applicable_to": ["Employee"]
            }
        ],
        "title_field": "full_name",
        "doctype": "Contact",
        "total_fields": 45
    }
}
```

---

### 3. `get_document_with_linked_data()` - Enhanced Document Retrieval

**Purpose**: Retrieve a single document along with its linked documents and communications.

**Endpoint**: `POST /api/method/sentra_core.api.read.get_document_with_linked_data`

**Parameters**:
- `doctype` (string, **required**): The DocType of the document
- `name` (string, **required**): The document ID/name
- `include_communications` (boolean, optional): Include communication history. Default: true
- `include_links` (boolean, optional): Include linked documents. Default: true

**Request Example**:
```json
{
    "doctype": "Contact",
    "name": "CONT-001",
    "include_communications": true,
    "include_links": true
}
```

**Response Format**:
```json
{
    "success": true,
    "data": {
        "name": "CONT-001",
        "full_name": "John Doe",
        "email_id": "john@example.com",
        "contact_type": "Customer",
        "city": "Mumbai",
        "linked_documents": [
            {
                "doctype": "Customer", 
                "name": "CUST-001",
                "title": "Doe Enterprises",
                "link_type": "Dynamic Link"
            },
            {
                "doctype": "Opportunity",
                "name": "OPP-001", 
                "title": "Website Redesign",
                "link_type": "Link Field (contact)"
            }
        ],
        "recent_communications": [
            {
                "name": "COMM-001",
                "subject": "Welcome Email",
                "communication_date": "2024-01-10",
                "sender": "sales@company.com",
                "communication_type": "Email"
            }
        ]
    }
}
```

---

## Saved Views Management

### 4. `save_list_view()` - Create/Update Saved Views

**Purpose**: Save a custom list view configuration that can be reused later.

**Endpoint**: `POST /api/method/sentra_core.api.read.save_list_view`

**Parameters**:
- `doctype` (string, **required**): The DocType this view is for
- `view_name` (string, **required**): Name of the saved view
- `filters` (object, optional): Filter conditions to save
- `sorts` (array, optional): Sort conditions `[{"field": "name", "direction": "asc"}]`
- `columns` (array, optional): Column display configuration for UI
- `fields` (array, optional): Fields to fetch from database
- `page_size` (integer, optional): Items per page. Default: 20
- `is_default` (boolean, optional): Make this the default view. Default: false
- `is_public` (boolean, optional): Share view with all users. Default: false
- `view_id` (string, optional): ID of existing view to update

**Request Example**:
```json
{
    "doctype": "Contact",
    "view_name": "Mumbai Customers",
    "filters": {
        "city": "Mumbai",
        "contact_type": "Customer", 
        "status": "Active"
    },
    "sorts": [
        {"field": "full_name", "direction": "asc"},
        {"field": "modified", "direction": "desc"}
    ],
    "fields": ["name", "full_name", "email_id", "mobile_no", "city", "company_name"],
    "page_size": 25,
    "is_default": false,
    "is_public": true
}
```

**Response Format**:
```json
{
    "success": true,
    "message": "View saved successfully",
    "data": {
        "view_id": "contact-mumbai-customers",
        "view_name": "Mumbai Customers",
        "is_default": false,
        "is_public": true
    }
}
```

---

### 5. `get_list_views()` - List All Saved Views

**Purpose**: Get all saved list views for a DocType accessible to the current user.

**Endpoint**: `POST /api/method/sentra_core.api.read.get_list_views`

**Parameters**:
- `doctype` (string, **required**): The DocType to get views for

**Request Example**:
```json
{
    "doctype": "Contact"
}
```

**Response Format**:
```json
{
    "success": true,
    "data": [
        {
            "name": "contact-mumbai-customers",
            "view_name": "Mumbai Customers",
            "owner": "user@example.com",
            "is_default": false,
            "is_public": true,
            "is_owner": true,
            "creation": "2024-01-15 10:30:00",
            "modified": "2024-01-16 14:20:00"
        },
        {
            "name": "contact-active-employees", 
            "view_name": "Active Employees",
            "owner": "admin@example.com",
            "is_default": true,
            "is_public": true,
            "is_owner": false,
            "creation": "2024-01-10 09:15:00",
            "modified": "2024-01-12 11:30:00"
        }
    ]
}
```

---

### 6. `get_list_view()` - Get Specific Saved View

**Purpose**: Get details of a specific saved list view configuration.

**Endpoint**: `POST /api/method/sentra_core.api.read.get_list_view`

**Parameters**:
- `view_name` (string, **required**): Name of the saved view
- `doctype` (string, optional): DocType (helps narrow search if multiple DocTypes have same view name)

**Request Example**:
```json
{
    "view_name": "Mumbai Customers",
    "doctype": "Contact"
}
```

**Response Format**:
```json
{
    "success": true,
    "data": {
        "view_id": "contact-mumbai-customers", 
        "view_name": "Mumbai Customers",
        "doctype": "Contact",
        "filters": {
            "city": "Mumbai",
            "contact_type": "Customer",
            "status": "Active"
        },
        "sorts": [
            {"field": "full_name", "direction": "asc"},
            {"field": "modified", "direction": "desc"}
        ],
        "columns": [],
        "fields": ["name", "full_name", "email_id", "mobile_no", "city"],
        "page_size": 25,
        "is_default": false,
        "is_public": true,
        "is_owner": true,
        "owner": "user@example.com",
        "modified": "2024-01-16 14:20:00"
    }
}
```

---

### 7. `delete_list_view()` - Delete Saved View

**Purpose**: Delete a saved list view (only owner can delete their own views).

**Endpoint**: `POST /api/method/sentra_core.api.read.delete_list_view`

**Parameters**:
- `view_name` (string, **required**): Name of the view to delete
- `doctype` (string, optional): DocType (helps narrow search)

**Request Example**:
```json
{
    "view_name": "Mumbai Customers",
    "doctype": "Contact"
}
```

**Response Format**:
```json
{
    "success": true,
    "message": "View deleted successfully"
}
```

---

## Complete Workflow Examples

### Example 1: Discover Fields and Create Custom View

```javascript
// Step 1: Discover available fields
POST /api/method/sentra_core.api.read.get_list_fields
{
    "doctype": "Contact"
}

// Step 2: Create a custom view using discovered fields
POST /api/method/sentra_core.api.read.save_list_view
{
    "doctype": "Contact",
    "view_name": "Sales Prospects",
    "filters": {
        "contact_type": "Customer",
        "status": "Active",
        "city": ["in", ["Mumbai", "Delhi", "Bangalore"]]
    },
    "fields": ["name", "full_name", "email_id", "mobile_no", "city", "company_name"],
    "sorts": [{"field": "modified", "direction": "desc"}],
    "page_size": 30,
    "is_public": true
}

// Step 3: Use the saved view to get data
POST /api/method/sentra_core.api.read.get_list
{
    "doctype": "Contact",
    "view": "Sales Prospects",
    "page": 1
}
```

### Example 2: Multi-DocType View Management

```javascript
// Create views for different DocTypes
POST /api/method/sentra_core.api.read.save_list_view
{
    "doctype": "Contact",
    "view_name": "Active Records",
    "filters": {"status": "Active"}
}

POST /api/method/sentra_core.api.read.save_list_view
{
    "doctype": "User", 
    "view_name": "Active Records",
    "filters": {"enabled": 1}
}

// Get specific view by specifying DocType
POST /api/method/sentra_core.api.read.get_list_view
{
    "view_name": "Active Records",
    "doctype": "Contact"
}
```

### Example 3: Advanced Filtering with View Override

```javascript
// Use saved view with additional filters
POST /api/method/sentra_core.api.read.get_list
{
    "doctype": "Contact",
    "view": "Sales Prospects",
    "filters": {
        "designation": ["like", "%Manager%"]  // Additional filter
    },
    "page_size": 50  // Override view's page size
}
```

---

## Error Handling

All APIs return consistent error responses:

```json
{
    "success": false,
    "message": "Detailed error message"
}
```

**Common Error Scenarios**:

1. **Permission Denied**:
```json
{
    "success": false,
    "message": "You don't have permission to access Contact"
}
```

2. **Invalid Fields**:
```json
{
    "success": false, 
    "message": "Invalid fields requested: invalid_field1, invalid_field2"
}
```

3. **Document Not Found**:
```json
{
    "success": false,
    "message": "Contact CONT-999999 not found"
}
```

4. **View Not Found**:
```json
{
    "success": false,
    "message": "View 'Nonexistent View' not found"
}
```

---

## Performance Tips

1. **Field Selection**: Always specify only the fields you need to improve query performance
2. **Appropriate Page Sizes**: Use 20-50 for UI lists, 100-500 for exports, avoid very large page sizes
3. **Indexed Filters**: Filter on indexed fields (name, creation, modified, status) for better performance
4. **Avoid Child Tables**: Child table fields cannot be fetched in list views and will be filtered out
5. **Use Saved Views**: Saved views provide consistent performance and reduce API complexity

---

## Security Features

1. **Permission Enforcement**: All APIs respect Frappe's role-based permission system
2. **SQL Injection Protection**: Input validation and parameterized queries prevent SQL injection
3. **Field Validation**: Requested fields are validated against DocType metadata
4. **User Isolation**: Users can only see their own views and public views from others
5. **XSS Prevention**: All output is properly escaped

---

## Integration Examples

### Frontend Integration (JavaScript)

```javascript
// Utility function for API calls
async function callReadAPI(method, data) {
    const response = await fetch(`/api/method/sentra_core.api.read.${method}`, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-Frappe-CSRF-Token': frappe.csrf_token
        },
        body: JSON.stringify(data)
    });
    return response.json();
}

// Get contacts with saved view
const contacts = await callReadAPI('get_list', {
    doctype: 'Contact',
    view: 'Mumbai Customers',
    page: 1
});

// Create a new view
const viewResult = await callReadAPI('save_list_view', {
    doctype: 'Contact',
    view_name: 'High Priority Leads',
    filters: { lead_score: [">", 80] },
    fields: ['name', 'full_name', 'email_id', 'lead_score'],
    is_public: false
});
```

### Python Integration

```python
import frappe
from sentra_core.api.read import get_list, save_list_view

# Get data programmatically
result = get_list(
    doctype="Contact",
    filters={"city": "Mumbai"},
    fields=["name", "full_name", "email_id"],
    page_size=100
)

if result["success"]:
    contacts = result["data"]["documents"]
    for contact in contacts:
        print(f"{contact['full_name']}: {contact['email_id']}")
```

This comprehensive documentation covers all aspects of the Read API, providing clear guidance for developers to effectively use these powerful data retrieval and management functions.