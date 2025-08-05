# Contact API Documentation

This documentation covers all custom Contact APIs in the Sentra Core application. All APIs return a consistent response format with `success`, `message`, and `data` fields.

## Authentication
All APIs require authentication. Include the session cookie in your requests:
```
Cookie: sid=<your-session-id>
```

## Response Format
All APIs return responses in this format:
```json
{
    "message": {
        "success": true/false,
        "message": "Success or error message",
        "data": { ... }  // Response data when successful
    }
}
```

## Important Field Notes

### Status Fields
- **status**: General contact status - "Active" or "Passive" (applies to Customer/Vendor)
- **employee_status**: Employee-specific status - "Active" or "Inactive" (applies only to Employee contacts)

### Contact Types and Categories
- **Contact Types**: "Customer", "Vendor", "Employee"
- **Contact Categories**:
  - Employee: "User" or "Non-User"
  - Customer/Vendor: "Individual" or "Organization"

---

## Contact CRUD Operations

### 1. Create Contact

**Endpoint**: `POST /api/method/sentra_core.api.contact.create_contact`

**Description**: Creates a new contact with validation for required fields and contact type-specific rules.

**Parameters**:
- `data` (object, required): Contact information
  - `first_name` (string, required): First name of the contact
  - `last_name` (string, optional): Last name of the contact
  - `email_id` (string, required*): Email address (*or mobile_no or instagram required)
  - `mobile_no` (string, required*): Mobile number (*or email_id or instagram required)
  - `instagram` (string, required*): Instagram handle (*or email_id or mobile_no required)
  - `contact_type` (string, required): Type of contact - "Customer", "Employee", or "Vendor"
  - `contact_category` (string, required): 
    - For Employee: "User" or "Non-User"
    - For Customer/Vendor: "Individual" or "Organization"
  - `city` (string, optional): City
  - `state` (string, optional): State
  - `notes` (string, optional): Additional notes

**Request Example**:
```json
{
    "data": {
        "first_name": "John",
        "last_name": "Doe",
        "email_id": "john.doe@example.com",
        "mobile_no": "9876543210",
        "contact_type": "Customer",
        "contact_category": "Individual",
        "city": "Mumbai",
        "state": "Maharashtra",
        "notes": "VIP Customer"
    }
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "message": "Contact created successfully",
        "data": {
            "name": "John Doe",
            "doctype": "Contact",
            "first_name": "John",
            "last_name": "Doe",
            "full_name": "John Doe",
            "email_id": "john.doe@example.com",
            "mobile_no": "9876543210",
            "contact_type": "Customer",
            "contact_category": "Individual",
            "city": "Mumbai",
            "state": "Maharashtra",
            "status": "Passive",
            "creation": "2025-08-05 16:30:00.123456",
            "owner": "user@example.com"
        }
    }
}
```

### 2. Update Contact

**Endpoint**: `POST /api/method/sentra_core.api.contact.update_contact`

**Description**: Updates an existing contact. Only provided fields will be updated.

**Parameters**:
- `contact_name` (string, required): Name/ID of the contact to update
- `data` (object, required): Fields to update

**Request Example**:
```json
{
    "contact_name": "John Doe",
    "data": {
        "city": "Delhi",
        "state": "Delhi",
        "status": "Active",
        "notes": "Updated to VIP Gold Customer"
    }
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "message": "Contact updated successfully",
        "data": {
            "name": "John Doe",
            "city": "Delhi",
            "state": "Delhi",
            "status": "Active",
            "notes": "Updated to VIP Gold Customer",
            "modified": "2025-08-05 17:00:00.123456"
        }
    }
}
```

### 3. Delete Contact

**Endpoint**: `POST /api/method/sentra_core.api.contact.delete_contact`

**Description**: Deletes a contact if it has no dependencies.

**Parameters**:
- `contact_name` (string, required): Name/ID of the contact to delete

**Request Example**:
```json
{
    "contact_name": "John Doe"
}
```

**Response Example (Success)**:
```json
{
    "message": {
        "success": true,
        "message": "Contact deleted successfully"
    }
}
```

**Response Example (Error - Has Dependencies)**:
```json
{
    "message": {
        "success": false,
        "message": "Cannot delete Contact John Doe. It is linked to:\nCustomer: CUST-00123"
    }
}
```

### 4. Get Contacts List

**Endpoint**: `POST /api/method/sentra_core.api.contact.get_contacts`

**Description**: Get paginated list of contacts with filtering, sorting, and search capabilities.

**Parameters**:
- `filters` (object, optional): Field-based filters (e.g., `{"contact_type": "Employee"}`)
- `fields` (array, optional): Fields to return. If not specified, returns default fields
- `order_by` (string, optional): Sort order (e.g., "full_name asc" or "modified desc")
- `page` (number, optional): Page number (default: 1)
- `page_size` (number, optional): Items per page (default: 20)
- `search_text` (string, optional): Search text (searches in full_name, email_id, mobile_no, city)

**Request Example**:
```json
{
    "filters": {
        "contact_type": "Employee",
        "employee_status": "Active"
    },
    "fields": ["name", "full_name", "employee_code", "department", "email_id"],
    "order_by": "full_name asc",
    "page": 1,
    "page_size": 25,
    "search_text": "Mumbai"
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "data": {
            "contacts": [
                {
                    "name": "Jane Smith",
                    "full_name": "Jane Smith",
                    "employee_code": "EMP001",
                    "department": "Sales",
                    "email_id": "jane.smith@company.com"
                },
                {
                    "name": "John Manager",
                    "full_name": "John Manager",
                    "employee_code": "EMP002",
                    "department": "Sales",
                    "email_id": "john.manager@company.com"
                }
            ],
            "pagination": {
                "total": 45,
                "page": 1,
                "page_size": 25,
                "total_pages": 2
            }
        }
    }
}
```

### 5. Get Contact Details

**Endpoint**: `POST /api/method/sentra_core.api.contact_read.get_contact_with_details`

**Description**: Get complete contact information including computed fields and linked documents.

**Parameters**:
- `contact_name` (string, required): Name/ID of the contact

**Request Example**:
```json
{
    "contact_name": "Jane Smith"
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "data": {
            "name": "Jane Smith",
            "first_name": "Jane",
            "last_name": "Smith",
            "full_name": "Jane Smith",
            "email_id": "jane.smith@company.com",
            "mobile_no": "9876543210",
            "contact_type": "Employee",
            "contact_category": "User",
            "employee_code": "EMP001",
            "department": "Sales",
            "designation": "Sales Manager",
            "date_of_joining": "2023-01-15",
            "employee_status": "Active",
            "dob": "1990-01-01",
            "age": 35,
            "years_of_service": 2,
            "city": "Mumbai",
            "state": "Maharashtra",
            "primary_contact_methods": {
                "email": "jane.smith@company.com",
                "mobile": "9876543210"
            },
            "linked_entities": [
                {
                    "doctype": "User",
                    "name": "jane.smith@company.com"
                }
            ],
            "recent_communications": [],
            "linked_documents": []
        }
    }
}
```

### 6. Get Contact Summary

**Endpoint**: `POST /api/method/sentra_core.api.contact_read.get_contact_summary`

**Description**: Get a brief summary of contact information for quick views/cards.

**Parameters**:
- `contact_name` (string, required): Name/ID of the contact

**Request Example**:
```json
{
    "contact_name": "Jane Smith"
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "data": {
            "name": "Jane Smith",
            "full_name": "Jane Smith",
            "first_name": "Jane",
            "last_name": "Smith",
            "email_id": "jane.smith@company.com",
            "mobile_no": "9876543210",
            "contact_type": "Employee",
            "contact_category": "User",
            "department": "Sales",
            "designation": "Sales Manager",
            "city": "Mumbai",
            "image": "",
            "age": 35,
            "years_of_service": 2
        }
    }
}
```

### 7. Validate Contact Deletion

**Endpoint**: `POST /api/method/sentra_core.api.contact_read.validate_contact_deletion`

**Description**: Check if a contact can be deleted by identifying all dependencies.

**Parameters**:
- `contact_name` (string, required): Name/ID of the contact to check

**Request Example**:
```json
{
    "contact_name": "Jane Smith"
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "data": {
            "can_delete": false,
            "linked_documents": [
                {
                    "doctype": "User",
                    "name": "jane.smith@company.com",
                    "type": "User Account"
                },
                {
                    "doctype": "Contact",
                    "name": "John Doe",
                    "title": "John Doe",
                    "type": "Manager Reference"
                }
            ],
            "message": "Contact has dependencies that must be resolved first"
        }
    }
}
```

---

## Bulk Operations

### 8. Bulk Upload Contacts (CSV/Excel)

**Endpoint**: `POST /api/method/sentra_core.api.contact.bulk_upload_contacts`

**Description**: Upload multiple contacts from CSV or Excel file.

**Parameters**:
- `file_content` (string, required): Base64 encoded file content
- `file_type` (string, optional): "csv" or "xlsx" (default: "csv")

**CSV Format**:
```csv
first_name,last_name,email_id,mobile_no,contact_type,contact_category,city
John,Doe,john@example.com,9876543210,Customer,Individual,Mumbai
Jane,Smith,jane@example.com,9876543211,Employee,User,Delhi
```

**Request Example**:
```json
{
    "file_content": "Zmlyc3RfbmFtZSxsYXN0X25hbWUsZW1haWxfaWQs...",
    "file_type": "csv"
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "message": "Uploaded 45 contacts successfully",
        "data": {
            "success_count": 45,
            "error_count": 3,
            "errors": [
                {
                    "row": 12,
                    "error": "Invalid mobile number format"
                },
                {
                    "row": 28,
                    "error": "Employee Code is mandatory for Employee contacts"
                }
            ]
        }
    }
}
```

### 9. Export Contacts

**Endpoint**: `POST /api/method/sentra_core.api.contact_bulk.bulk_export_contacts`

**Description**: Export contacts to CSV or Excel format.

**Parameters**:
- `filters` (object, optional): Filters to apply before export
- `format` (string, optional): "csv" or "xlsx" (default: "csv")

**Request Example**:
```json
{
    "filters": {
        "contact_type": "Employee",
        "employee_status": "Active"
    },
    "format": "csv"
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "data": {
            "content": "Zmlyc3RfbmFtZSxsYXN0X25hbWUsZW1haWxfaWQs...",
            "filename": "contacts_20250805_163000.csv",
            "format": "csv",
            "total_records": 45
        }
    }
}
```

### 10. Bulk Update Contacts

**Endpoint**: `POST /api/method/sentra_core.api.contact.bulk_update_contacts`

**Description**: Update multiple contacts in one operation.

**Parameters**:
- `updates` (array, required): Array of update objects
  - Each object must have `contact_name` and fields to update

**Request Example**:
```json
{
    "updates": [
        {
            "contact_name": "John Doe",
            "city": "Mumbai",
            "status": "Active"
        },
        {
            "contact_name": "Jane Smith",
            "department": "Marketing",
            "employee_status": "Active"
        }
    ]
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "message": "Updated 2 contacts",
        "data": {
            "success_count": 2,
            "error_count": 0,
            "errors": []
        }
    }
}
```

### 11. Bulk Delete Contacts

**Endpoint**: `POST /api/method/sentra_core.api.contact.bulk_delete_contacts`

**Description**: Delete multiple contacts in one operation.

**Parameters**:
- `contact_names` (array, required): Array of contact names to delete

**Request Example**:
```json
{
    "contact_names": ["Test Contact 1", "Test Contact 2", "Test Contact 3"]
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "message": "Deleted 2 contacts",
        "data": {
            "success_count": 2,
            "error_count": 1,
            "errors": [
                {
                    "contact": "Test Contact 2",
                    "error": "Cannot delete - linked to Customer CUST-00123"
                }
            ]
        }
    }
}
```

---

## Employee-Specific Operations

### 12. Get Employee Hierarchy

**Endpoint**: `POST /api/method/sentra_core.api.contact_read.get_contact_hierarchy`

**Description**: Get reporting hierarchy for an employee contact.

**Parameters**:
- `contact_name` (string, required): Name/ID of the employee contact

**Request Example**:
```json
{
    "contact_name": "Jane Smith"
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "data": {
            "contact": {
                "name": "Jane Smith",
                "full_name": "Jane Smith",
                "designation": "Sales Manager",
                "employee_code": "EMP001"
            },
            "manager_chain": [
                {
                    "name": "John Manager",
                    "full_name": "John Manager",
                    "designation": "Sales Director",
                    "manager": "CEO Name"
                },
                {
                    "name": "CEO Name",
                    "full_name": "CEO Name",
                    "designation": "Chief Executive Officer",
                    "manager": null
                }
            ],
            "direct_reports": [
                {
                    "name": "Alice Johnson",
                    "full_name": "Alice Johnson",
                    "designation": "Sales Executive",
                    "employee_status": "Active"
                },
                {
                    "name": "Bob Wilson",
                    "full_name": "Bob Wilson",
                    "designation": "Sales Executive",
                    "employee_status": "Active"
                }
            ],
            "team_size": 8
        }
    }
}
```

---

## AI-Powered Operations

### 13. Search Contacts with AI

**Endpoint**: `POST /api/method/sentra_core.api.contact.search_contacts_ai`

**Description**: Search contacts using natural language queries. Currently supports basic keyword matching for cities (Mumbai, Delhi, Bangalore, Chennai, Kolkata, Pune), contact types (vendor/supplier, customer/client, employee), and status (active/passive/inactive). Note: 'inactive' is mapped to 'Passive' status.

**Parameters**:
- `query` (string, required): Natural language search query

**Request Example**:
```json
{
    "query": "all active employees in Mumbai sales department"
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "data": {
            "contacts": [
                {
                    "name": "Jane Smith",
                    "full_name": "Jane Smith",
                    "email_id": "jane.smith@company.com",
                    "contact_type": "Employee",
                    "department": "Sales",
                    "city": "Mumbai",
                    "employee_status": "Active"
                }
            ],
            "pagination": {
                "total": 12,
                "page": 1,
                "page_size": 20,
                "total_pages": 1
            }
        }
    }
}
```

### 14. Delete Contacts with AI

**Endpoint**: `POST /api/method/sentra_core.api.contact.delete_contacts_ai`

**Description**: Delete contacts matching natural language criteria.

**Parameters**:
- `query` (string, required): Natural language deletion query
- `dry_run` (boolean, optional): If true, preview what will be deleted without actually deleting (default: true)

**Request Example (Preview)**:
```json
{
    "query": "delete all passive vendor contacts from Mumbai",
    "dry_run": true
}
```

**Response Example (Preview)**:
```json
{
    "message": {
        "success": true,
        "message": "Found 8 contacts matching your query",
        "data": {
            "contacts": [
                {
                    "name": "ABC Suppliers",
                    "full_name": "ABC Suppliers",
                    "contact_type": "Vendor",
                    "city": "Mumbai",
                    "status": "Passive"
                }
            ],
            "would_delete": 8,
            "dry_run": true
        }
    }
}
```

### 15. Create Contact from AI

**Endpoint**: `POST /api/method/sentra_core.api.contact.create_contact_from_ai`

**Description**: Parse unstructured text to create contact (business cards, email signatures, etc.).

**Parameters**:
- `unstructured_data` (string, required): Raw text containing contact information
- `data_type` (string, optional): Type of data - "text", "business_card", "email_signature" (default: "text")

**Request Example**:
```json
{
    "unstructured_data": "Rajesh Kumar\nSales Director\nXYZ Corporation\nEmail: rajesh@xyz.com\nMobile: 9876543210\nMumbai, Maharashtra",
    "data_type": "business_card"
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "message": "Data parsed successfully",
        "data": {
            "doctype": "Contact",
            "first_name": "Rajesh",
            "last_name": "Kumar",
            "designation": "Sales Director",
            "company_name": "XYZ Corporation",
            "email_id": "rajesh@xyz.com",
            "mobile_no": "9876543210",
            "city": "Mumbai",
            "state": "Maharashtra",
            "contact_type": "Customer",
            "contact_category": "Individual"
        },
        "require_confirmation": true
    }
}
```

---

## Utility Operations

### 16. Get Contact Metadata

**Endpoint**: `POST /api/method/sentra_core.api.contact.get_contact_meta`

**Description**: Get metadata about the Contact DocType including field definitions and options.

**Parameters**: None

**Request Example**:
```json
{}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "data": {
            "fields": [
                {
                    "fieldname": "first_name",
                    "label": "First Name",
                    "fieldtype": "Data",
                    "options": null,
                    "reqd": 0,
                    "unique": 0,
                    "default": null
                },
                {
                    "fieldname": "email_id",
                    "label": "Email Address",
                    "fieldtype": "Data",
                    "options": "Email",
                    "reqd": 0,
                    "unique": 0,
                    "default": null
                },
                {
                    "fieldname": "contact_type",
                    "label": "Contact Type",
                    "fieldtype": "Link",
                    "options": "Contact Type",
                    "reqd": 0,
                    "unique": 0,
                    "default": null
                }
                // ... more fields
            ],
            "title_field": "full_name",
            "search_fields": ["email_id"],
            "sort_field": "creation",
            "sort_order": "DESC"
        }
    }
}
```

---

## List View Settings APIs

### 17. Save List View

**Endpoint**: `POST /api/method/sentra_core.api.contact_list_settings.save_list_view`

**Description**: Save a custom list view configuration with filters, sorting, and column settings.

**Parameters**:
- `view_name` (string, required): Name for the saved view
- `filters` (object, optional): Filter conditions
- `sorts` (array, optional): Sort configuration
- `columns` (array, optional): Column display configuration
- `rows` (array, optional): Fields to fetch from database
- `page_size` (number, optional): Items per page (default: 20)
- `is_default` (boolean, optional): Make this the default view
- `is_public` (boolean, optional): Share view with all users
- `view_id` (string, optional): ID of existing view to update

**Request Example**:
```json
{
    "view_name": "Active Mumbai Employees",
    "filters": {
        "contact_type": "Employee",
        "employee_status": "Active",
        "city": "Mumbai"
    },
    "sorts": [
        {"field": "department", "direction": "asc"},
        {"field": "full_name", "direction": "asc"}
    ],
    "columns": [
        {"label": "Full Name", "fieldname": "full_name", "width": "10rem"},
        {"label": "Employee Code", "fieldname": "employee_code", "width": "8rem"},
        {"label": "Department", "fieldname": "department", "width": "8rem"}
    ],
    "rows": ["name", "full_name", "employee_code", "department", "email_id"],
    "page_size": 25,
    "is_default": true,
    "is_public": false
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "message": "List view saved successfully",
        "data": {
            "name": "VIEW-001",
            "view_name": "Active Mumbai Employees",
            "filters": {
                "contact_type": "Employee",
                "employee_status": "Active",
                "city": "Mumbai"
            },
            "sorts": [
                {"field": "department", "direction": "asc"},
                {"field": "full_name", "direction": "asc"}
            ],
            "columns": [
                {"label": "Full Name", "fieldname": "full_name", "width": "10rem"},
                {"label": "Employee Code", "fieldname": "employee_code", "width": "8rem"},
                {"label": "Department", "fieldname": "department", "width": "8rem"}
            ],
            "rows": ["name", "full_name", "employee_code", "department", "email_id"],
            "page_size": 25,
            "is_default": 1,
            "is_public": 0
        }
    }
}
```

### 18. Get All List Views

**Endpoint**: `GET /api/method/sentra_core.api.contact_list_settings.get_list_views`

**Description**: Get all saved list views accessible to the current user.

**Parameters**: None

**Response Example**:
```json
{
    "message": {
        "success": true,
        "data": [
            {
                "name": "VIEW-001",
                "view_name": "Active Mumbai Employees",
                "filters": {
                    "contact_type": "Employee",
                    "employee_status": "Active",
                    "city": "Mumbai"
                },
                "sorts": [
                    {"field": "full_name", "direction": "asc"}
                ],
                "columns": [
                    {"label": "Full Name", "fieldname": "full_name", "width": "10rem"}
                ],
                "rows": ["name", "full_name", "employee_code"],
                "is_default": 1,
                "is_public": 0,
                "is_mine": true,
                "owner": "Administrator",
                "modified": "2025-08-05 11:29:49.128161"
            }
        ]
    }
}
```

### 19. Get Contacts with View

**Endpoint**: `POST /api/method/sentra_core.api.contact_list_settings.get_contacts_with_view`

**Description**: Load contacts using a saved view configuration.

**Parameters**:
- `view_id` (string, optional): ID of saved view to use
- `page` (number, required): Page number
- `page_size` (number, optional): Override saved page size
- `override_filters` (object, optional): Additional filters to apply
- `override_sorts` (array, optional): Override saved sorting
- `search_text` (string, optional): Search within results

**Request Example**:
```json
{
    "view_id": "VIEW-001",
    "page": 1,
    "search_text": "Sales"
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "data": {
            "contacts": [
                {
                    "name": "Jane Smith",
                    "full_name": "Jane Smith",
                    "employee_code": "EMP001",
                    "department": "Sales"
                }
            ],
            "pagination": {
                "total": 5,
                "page": 1,
                "page_size": 20,
                "total_pages": 1
            },
            "applied_view": {
                "name": "VIEW-001",
                "view_name": "Active Mumbai Employees",
                "filters": {
                    "contact_type": "Employee",
                    "employee_status": "Active",
                    "city": "Mumbai"
                },
                "sorts": [{"field": "full_name", "direction": "asc"}],
                "columns": [{"label": "Full Name", "fieldname": "full_name", "width": "10rem"}],
                "rows": ["name", "full_name", "employee_code"],
                "page_size": 20
            }
        }
    }
}
```

### 20. Delete List View

**Endpoint**: `POST /api/method/sentra_core.api.contact_list_settings.delete_list_view`

**Description**: Delete a saved list view.

**Parameters**:
- `view_id` (string, required): ID of the view to delete

**Request Example**:
```json
{
    "view_id": "VIEW-001"
}
```

**Response Example**:
```json
{
    "message": {
        "success": true,
        "message": "List view deleted successfully"
    }
}
```

### 21. Get Available List Fields

**Endpoint**: `GET /api/method/sentra_core.api.doctype_fields.get_list_fields?doctype=Contact`

**Description**: Get all available fields for the Contact DocType that can be used in list views.

**Parameters**:
- `doctype` (string, required): DocType name (use "Contact" for contacts)

**Response Example**:
```json
{
    "message": {
        "success": true,
        "data": {
            "fields": [
                {
                    "fieldname": "full_name",
                    "label": "Full Name",
                    "fieldtype": "Data",
                    "in_list_view": 1,
                    "in_standard_filter": 0,
                    "applicable_to": "all"
                },
                {
                    "fieldname": "employee_code",
                    "label": "Employee Code",
                    "fieldtype": "Data",
                    "in_list_view": 0,
                    "in_standard_filter": 0,
                    "applicable_to": "all"
                }
                // ... more fields
            ],
            "title_field": "full_name",
            "doctype": "Contact",
            "total_fields": 86
        }
    }
}
```

---

## Error Handling

All APIs return consistent error responses:

```json
{
    "message": {
        "success": false,
        "message": "Detailed error message here"
    }
}
```

Common error scenarios:
- Missing required fields
- Invalid field values
- Permission denied
- Record not found
- Dependency conflicts (for deletion)
- Validation errors