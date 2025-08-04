# Contact API Documentation for Frontend Team

## Table of Contents
1. [Authentication](#authentication)
2. [Base URLs & Headers](#base-urls--headers)
3. [Response Format](#response-format)
4. [Field Definitions](#field-definitions)
5. [Validation Rules](#validation-rules)
6. [CRUD Operations](#crud-operations)
7. [Bulk Operations](#bulk-operations)
8. [Enhanced Read Operations](#enhanced-read-operations)
9. [Error Handling](#error-handling)
10. [Frontend Integration Examples](#frontend-integration-examples)

---

## Authentication

All APIs require authentication. Use one of these methods:


### Token Authentication (Recommended for Mobile/API)
```javascript
// Add to all requests
headers: {
    'Authorization': 'token api_key:api_secret'
}
```

---

## Base URLs & Headers

**Base URL**: `http://sentra.localhost:8000` (adjust for your environment)

**Required Headers**:
```javascript
{
    'Content-Type': 'application/json',
    'Accept': 'application/json'
}
```

---

## Response Format

All APIs return consistent JSON responses:

### Success Response
```javascript
{
    "success": true,
    "message": "Operation completed successfully",
    "data": {
        // Response data here
    }
}
```

### Error Response
```javascript
{
    "success": false,
    "message": "Error description",
    "exc_type": "ValidationError",  // Optional
    "exception": "Detailed error"   // Optional
}
```

---

## Field Definitions

### Core Fields
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `name` | String | Auto | full name auto generated |
| `first_name` | String | Yes* | Contact's first name |
| `last_name` | String | No | Contact's last name |
| `full_name` | String | Auto | Auto-generated from names |

### Contact Information (At least ONE required)
| Field | Type | Required | Description |
|-------|------|----------|-------------|
| `email_id` | Email | Conditional | Primary email address |
| `mobile_no` | Phone | Conditional | Primary mobile number |
| `instagram` | String | Conditional | Instagram handle |

### Child Tables
| Table | Description | Fields |
|-------|-------------|--------|
| `email_ids` | Multiple emails | `email_id` (Email), `is_primary` (Check) |
| `phone_nos` | Multiple phones | `phone` (Phone), `is_primary_mobile_no` (Check) |

### Address Fields
| Field | Type | Description |
|-------|------|-------------|
| `address_line1` | String | Street address |
| `address_line2` | String | Additional address |
| `city` | String | City name |
| `state` | String | State/Province |
| `country` | String | Country |
| `pincode` | String | Postal code |

### Business Fields
| Field | Type | Description |
|-------|------|-------------|
| `contact_type` | Link | Customer, Vendor, Employee, Partner |
| `contact_category` | Link | Individual, Corporate, etc. |
| `company_name` | String | Organization name |
| `designation` | String | Job title |
| `gstin` | String | GST Identification Number |
| `vendor_type` | Link | Required if contact_type = "Vendor" |

### Employee-Specific Fields
| Field | Type | Required For Employee | Description |
|-------|------|----------------------|-------------|
| `employee_code` | String | Yes | Unique employee identifier |
| `date_of_joining` | Date | No | Employment start date |
| `employee_status` | Select | No | Active, Inactive |
| `manager` | Link | No | Reports to (Contact) |
| `direct_supervisor` | Link | No | Direct supervisor |
| `work_email` | Email | No | Work email address |
| `user_role` | Link | No | System role |
| `travel_approval_limit` | Currency | No | Approval limit for travel |
| `booking_permissions` | Select | No | Self Only, Team, Department, All |

### Personal Fields
| Field | Type | Description |
|-------|------|-------------|
| `dob` | Date | Date of birth |
| `gender` | Link | Gender |
| `notes` | Long Text | Additional notes |

### System Fields (Read-Only)
| Field | Type | Description |
|-------|------|-------------|
| `creation` | Datetime | Created timestamp |
| `modified` | Datetime | Last modified timestamp |
| `owner` | Link | Created by user |
| `modified_by` | Link | Last modified by user |

---

## Validation Rules

### 🔴 Mandatory Validations (Will cause API failure)

#### Contact Method Requirement
At least ONE of these must be provided:
- `instagram`
- OR entries in `email_ids` child table
- OR entries in `phone_nos` child table

#### Contact Type Specific
- **Employee**: `employee_code` is mandatory
- **Vendor**: `vendor_type` is mandatory

#### Format Validations
- **Mobile Number**: Indian format - 10 digits starting with 6-9, optional +91 prefix
  - ✅ Valid: `9876543210`, `+91-9876543210`, `+91 9876543210`
  - ❌ Invalid: `123`, `0123456789`, `5876543210`

- **GSTIN**: 15 characters, specific pattern
  - ✅ Valid: `27AAPFU0939F1ZV`
  - ❌ Invalid: `INVALID123`, `27AAPFU0939F1Z` (14 chars)

#### Business Logic
- Employee cannot be their own manager
- Employee must be 18+ years old at joining date
- No circular manager hierarchy (A → B → A)

### 🟡 Warning Validations (Will show warnings but allow operation)

- Duplicate email addresses
- Missing GSTIN for Airline/Hotel/Transport vendors
- Employee status change from Active to Inactive

### ✨ Auto-Corrections
- GSTIN automatically converted to uppercase
- Primary flags auto-managed in child tables
- Full name auto-generated from first/middle/last names

---

## CRUD Operations

### 1. Create Contact

**Endpoint**: `POST /api/resource/Contact`

**Basic Example**:
```javascript
const response = await fetch('/api/resource/Contact', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        first_name: "John",
        last_name: "Doe",
        email_id: "john.doe@example.com",
        mobile_no: "9876543210",
        contact_type: "Customer",
        city: "Mumbai"
    })
});
```

**Employee Example**:
```javascript
{
    first_name: "Jane",
    last_name: "Smith",
    contact_type: "Employee",
    employee_code: "EMP001",
    date_of_joining: "2024-01-15",
    dob: "1990-01-01",
    email_ids: [
        {
            email_id: "jane.smith@company.com",
            is_primary: 1
        }
    ]
}
```

**Vendor Example**:
```javascript
{
    first_name: "ABC Airlines",
    contact_type: "Vendor",
    vendor_type: "Airline",
    gstin: "27AAPFU0939F1ZV",
    email_id: "contact@abcairlines.com",
    phone_nos: [
        {
            phone: "011-23456789",
            is_primary_phone: 1
        },
        {
            phone: "9876543210",
            is_primary_mobile_no: 1
        }
    ]
}
```

### 2. Read Contact

**Endpoint**: `GET /api/resource/Contact/{full_name}`

```javascript
const contact = await fetch('/api/resource/Contact/arvis');
```

**With Specific Fields**:
```javascript
const contact = await fetch('/api/resource/Contact/arvis?fields=["name","full_name","email_id","mobile_no"]');
```

### 3. Update Contact

**Endpoint**: `PUT /api/resource/Contact/{full_name}`

```javascript
const response = await fetch('/api/resource/Contact/arvis', {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        city: "Delhi",
        mobile_no: "9999999999"
    })
});
```

**Update Child Tables**:
```javascript
{
    email_ids: [
        {
            email_id: "new_primary@example.com",
            is_primary: 1
        },
        {
            email_id: "secondary@example.com",
            is_primary: 0
        }
    ]
}
```

### 4. Delete Contact

**Endpoint**: `DELETE /api/resource/Contact/{full_name}`

```javascript
const response = await fetch('/api/resource/Contact/arvis', {
    method: 'DELETE'
});
```

### 5. List Contacts

**Endpoint**: `GET /api/resource/Contact`

**Basic List**:
```javascript
const contacts = await fetch('/api/resource/Contact?limit_page_length=20');
```

**With Filters**:
```javascript
const url = '/api/resource/Contact?' + new URLSearchParams({
    'filters': JSON.stringify([["contact_type", "=", "Employee"]]),
    'fields': JSON.stringify(["name", "full_name", "employee_code"]),
    'limit_page_length': '20',
    'limit_start': '0'
});
```

**Available Filter Operators**:
- `=` (equals)
- `!=` (not equals)
- `>`, `<`, `>=`, `<=` (comparisons)
- `like` (contains)
- `in` (in list)
- `not in` (not in list)

---

## Bulk Operations

### 1. Bulk Create

**Endpoint**: `POST /api/method/sentra_core.api.contact_bulk.bulk_create_contacts`

**Limit**: 500 contacts per request

```javascript
const response = await fetch('/api/method/sentra_core.api.contact_bulk.bulk_create_contacts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        contacts: [
            {
                first_name: "John",
                last_name: "Doe",
                email_id: "john@example.com",
                contact_type: "Customer"
            },
            {
                first_name: "Jane",
                last_name: "Smith",
                mobile_no: "9876543210",
                contact_type: "Employee",
                employee_code: "EMP001"
            }
        ]
    })
});
```

**Response**:
```javascript
{
    "success": true,
    "message": "Created 2 contacts, 0 failed",
    "data": {
        "success_count": 2,
        "failed_count": 0,
        "total_requested": 2,
        "created_contacts": [
            {
                "index": 0,
                "name": "arvis",
                "full_name": "John Doe"
            }
        ],
        "failed_contacts": []
    }
}
```

### 2. Bulk Update

**Endpoint**: `POST /api/method/sentra_core.api.contact_bulk.bulk_update_contacts`

**Limit**: 500 contacts per request

```javascript
const response = await fetch('/api/method/sentra_core.api.contact_bulk.bulk_update_contacts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        updates: [
            {
                contact_name: "arvis",
                city: "Mumbai",
                state: "Maharashtra"
            },
            {
                contact_name: "kettier",
                mobile_no: "9999999999"
            }
        ]
    })
});
```

### 3. Bulk Delete

**Endpoint**: `POST /api/method/sentra_core.api.contact_bulk.bulk_delete_contacts`

**Limit**: 100 contacts per request (for safety)

```javascript
const response = await fetch('/api/method/sentra_core.api.contact_bulk.bulk_delete_contacts', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        contact_names: ["arvis", "kettier"],
        force_delete: false  // Optional: skip some dependency checks
    })
});
```

### 4. CSV Import

**Endpoint**: `POST /api/method/sentra_core.api.contact_bulk.bulk_create_from_csv`

```javascript
// First, convert file to base64
const fileToBase64 = (file) => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
    });
};

const base64Content = await fileToBase64(csvFile);

const response = await fetch('/api/method/sentra_core.api.contact_bulk.bulk_create_from_csv', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
        file_content: base64Content,
        file_type: "csv",
        validate_only: false  // Set to true for validation preview
    })
});
```

### 5. Get Import Template

**Endpoint**: `GET /api/method/sentra_core.api.contact_bulk.get_bulk_import_template`

```javascript
const template = await fetch('/api/method/sentra_core.api.contact_bulk.get_bulk_import_template');
const data = await template.json();

// Download the template
const blob = new Blob([atob(data.data.content)], { type: 'text/csv' });
const url = window.URL.createObjectURL(blob);
const a = document.createElement('a');
a.href = url;
a.download = data.data.filename;
a.click();
```

### 6. Export Contacts

**Endpoint**: `GET /api/method/sentra_core.api.contact_bulk.bulk_export_contacts`

```javascript
const exportParams = new URLSearchParams({
    'filters': JSON.stringify({"contact_type": "Employee"}),
    'fields': JSON.stringify(["name", "full_name", "employee_code", "email_id"]),
    'format': 'csv'
});

const response = await fetch(`/api/method/sentra_core.api.contact_bulk.bulk_export_contacts?${exportParams}`);
```

---

## Enhanced Read Operations

### 1. Contact with Details

**Endpoint**: `GET /api/method/sentra_core.api.contact_read.get_contact_with_details`

Returns contact with computed fields (age, years_of_service) and linked data.

```javascript
const response = await fetch('/api/method/sentra_core.api.contact_read.get_contact_with_details?contact_name=arvis');
```

### 2. Contact Summary

**Endpoint**: `GET /api/method/sentra_core.api.contact_read.get_contact_summary`

Lightweight contact data for cards/previews.

```javascript
const response = await fetch('/api/method/sentra_core.api.contact_read.get_contact_summary?contact_name=arvis');
```

### 3. Employee Hierarchy

**Endpoint**: `GET /api/method/sentra_core.api.contact_read.get_contact_hierarchy`

Returns manager chain and direct reports (Employee contacts only).

```javascript
const response = await fetch('/api/method/sentra_core.api.contact_read.get_contact_hierarchy?contact_name=arvis');
```

### 4. Deletion Validation

**Endpoint**: `GET /api/method/sentra_core.api.contact_read.validate_contact_deletion`

Check if contact can be safely deleted (dry-run).

```javascript
const response = await fetch('/api/method/sentra_core.api.contact_read.validate_contact_deletion?contact_name=arvis');
```

---

## Error Handling

### Common HTTP Status Codes
- `200`: Success
- `400`: Bad Request (validation errors)
- `401`: Unauthorized
- `403`: Forbidden (permission denied)
- `404`: Not Found
- `500`: Internal Server Error

### Error Categories

#### Validation Errors
```javascript
{
    "success": false,
    "message": "Employee Code is mandatory for Employee contacts",
    "exc_type": "ValidationError"
}
```

#### Permission Errors
```javascript
{
    "success": false,
    "message": "Not permitted to create Contact",
    "exc_type": "PermissionError"
}
```

#### Dependency Errors (Delete)
```javascript
{
    "success": false,
    "message": "Cannot delete Contact John Doe. It is linked to:\nCustomer: CUST-001\nManager of: Jane Smith (CONT-002)"
}
```

### Frontend Error Handling Best Practices

```javascript
try {
    const response = await fetch('/api/resource/Contact', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(contactData)
    });
    
    const result = await response.json();
    
    if (!result.success) {
        // Handle API-level errors
        showError(result.message);
        return;
    }
    
    // Handle success
    showSuccess('Contact created successfully');
    
} catch (error) {
    // Handle network/parsing errors
    showError('Network error: ' + error.message);
}
```

---
## Performance Tips

1. **Use Pagination**: Always limit list queries with `limit_page_length`
2. **Select Specific Fields**: Use `fields` parameter to reduce payload size
3. **Batch Operations**: Use bulk APIs for multiple operations
4. **Cache Responses**: Cache dropdown data (contact types, categories)
5. **Debounce Search**: Delay search requests by 300ms
6. **Validate Client-Side**: Reduce server round trips with client validation

---



*Last Updated: 04-08-25*
*API Version: v1.0*