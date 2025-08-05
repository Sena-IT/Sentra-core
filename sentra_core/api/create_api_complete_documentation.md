# Create API Complete Documentation

## Overview

The Create API provides a comprehensive set of functions for creating documents in Frappe/ERPNext with built-in validation, type conversion, and error handling. It's designed to be robust enough for AI bots, automated systems, and frontend applications.

### Key Features

- **Automatic Validation**: Pre-validates data before creation
- **Type Conversion**: Automatically converts common data types (strings to numbers, dates, booleans)
- **Comprehensive Error Messages**: Clear, actionable error messages instead of technical errors
- **Bulk Operations**: Support for creating multiple documents efficiently
- **Schema Discovery**: Dynamically discover field information for any DocType
- **AI-Friendly**: Handles messy, unstructured data with intelligent parsing

## Table of Contents

1. [create_document](#1-create_document) - Create a single document
2. [bulk_upload_documents](#2-bulk_upload_documents) - Bulk upload from CSV/Excel
3. [create_document_from_unstructured_data](#3-create_document_from_unstructured_data) - Create from unstructured text
4. [create_multiple_documents](#4-create_multiple_documents) - Create multiple documents in one transaction
5. [duplicate_document](#5-duplicate_document) - Duplicate an existing document
6. [get_document_template](#6-get_document_template) - Get templates for bulk upload
7. [get_doctype_create_schema](#7-get_doctype_create_schema) - Get complete field information
8. [validate_document_data](#8-validate_document_data) - Pre-validate data before creation

---

## 1. create_document

Creates a single document with automatic validation and type conversion.

### Purpose
- Primary method for creating any document in Frappe
- Automatically validates data using schema
- Converts data types (e.g., "yes" → 1, "25/12/2024" → "2024-12-25")
- Returns clear validation errors if data is invalid

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| doctype | string | Yes | The DocType to create (e.g., "Contact", "ToDo") |
| data | dict/string | Yes | Document data as dictionary or JSON string |
| skip_validation | boolean | No | Skip pre-validation (default: False) |

### Request Example

```python
# Python
result = frappe.call(
    "sentra_core.api.create.create_document",
    doctype="Contact",
    data={
        "first_name": "John",
        "last_name": "Doe",
        "email_ids": [
            {"email_id": "john.doe@example.com", "is_primary": 1}
        ],
        "phone_nos": [
            {"phone": "+919876543210", "is_primary_mobile_no": 1}
        ],
        "contact_type": "Customer",
        "city": "Mumbai"
    }
)
```

```bash
# cURL
curl -X POST https://your-site.com/api/method/sentra_core.api.create.create_document \
  -H "Authorization: token api_key:api_secret" \
  -H "Content-Type: application/json" \
  -d '{
    "doctype": "Contact",
    "data": {
        "first_name": "John",
        "last_name": "Doe",
        "email_ids": [{"email_id": "john@example.com", "is_primary": 1}]
    }
}'
```

### Response Examples

**Success Response:**
```json
{
    "success": true,
    "message": "Contact created successfully",
    "data": {
        "name": "John Doe",
        "owner": "Administrator",
        "creation": "2024-12-20 10:30:45.123456",
        "modified": "2024-12-20 10:30:45.123456",
        "modified_by": "Administrator",
        "docstatus": 0,
        "first_name": "John",
        "last_name": "Doe",
        "full_name": "John Doe",
        "email_id": "john.doe@example.com",
        "mobile_no": "+919876543210",
        "contact_type": "Customer",
        "city": "Mumbai",
        "doctype": "Contact"
    }
}
```

**Validation Error Response:**
```json
{
    "success": false,
    "message": "Validation failed",
    "validation_errors": [
        "Status must be one of: Open, Closed, Cancelled",
        "Description is required",
        "Due Date must be a valid date (YYYY-MM-DD format preferred)"
    ],
    "validation_warnings": [],
    "data": null
}
```

### Type Conversion Examples

The API automatically converts common data types:

| Input | Converted To | Field Type |
|-------|--------------|------------|
| "123" | 123 | Int |
| "45.67" | 45.67 | Float/Currency |
| "yes", "true", "1" | 1 | Check (Boolean) |
| "no", "false", "0" | 0 | Check (Boolean) |
| "25/12/2024" | "2024-12-25" | Date |
| "   " (whitespace) | Error: "cannot be empty or whitespace only" | Required fields |

---

## 2. bulk_upload_documents

Upload multiple documents from CSV or Excel files.

### Purpose
- Bulk create documents from spreadsheet data
- Supports field mapping for custom column names
- Returns detailed success/error information for each row
- Automatically handles type conversion

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| doctype | string | Yes | The DocType to create |
| file_content | string | Yes | Base64 encoded file content |
| file_type | string | No | File type: "csv" or "xlsx" (default: "csv") |
| field_mapping | dict/string | No | Map CSV columns to DocType fields |

### Request Example

```python
# Python
import base64
import csv
import io

# Create CSV content
csv_buffer = io.StringIO()
writer = csv.DictWriter(csv_buffer, fieldnames=["title", "content", "public"])
writer.writeheader()
writer.writerows([
    {"title": "Note 1", "content": "Content 1", "public": "1"},
    {"title": "Note 2", "content": "Content 2", "public": "0"},
    {"title": "Note 3", "content": "Content 3", "public": "yes"}
])

# Encode to base64
csv_base64 = base64.b64encode(csv_buffer.getvalue().encode()).decode()

# Upload
result = frappe.call(
    "sentra_core.api.create.bulk_upload_documents",
    doctype="Note",
    file_content=csv_base64,
    file_type="csv"
)
```

### Response Example

```json
{
    "success": true,
    "message": "Uploaded 3 Note documents successfully",
    "data": {
        "success_count": 3,
        "error_count": 0,
        "errors": [],
        "created_documents": ["Note 1", "Note 2", "Note 3"]
    }
}
```

### With Field Mapping

```python
# CSV has different column names
field_mapping = {
    "task_name": "description",
    "task_status": "status",
    "task_priority": "priority"
}

result = frappe.call(
    "sentra_core.api.create.bulk_upload_documents",
    doctype="ToDo",
    file_content=csv_base64,
    file_type="csv",
    field_mapping=field_mapping
)
```

### Error Handling Example

```json
{
    "success": true,
    "message": "Uploaded 2 Contact documents successfully",
    "data": {
        "success_count": 2,
        "error_count": 1,
        "errors": [
            {
                "row": 3,
                "error": "At least one contact method is required: Email, Mobile Number, or Instagram ID",
                "data": {"first_name": "John", "last_name": "Doe"}
            }
        ],
        "created_documents": ["Jane Smith", "Bob Wilson"]
    }
}
```

---

## 3. create_document_from_unstructured_data

Create documents from unstructured text using pattern matching and AI-friendly parsing.

### Purpose
- Parse business cards, emails, or any unstructured text
- Extract data using regex patterns or basic heuristics
- Returns parsed data for review before creation
- Supports custom parsing rules

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| doctype | string | Yes | The DocType to create |
| unstructured_data | string | Yes | Raw text to parse |
| data_type | string | No | Type of data: "text", "json", "xml" (default: "text") |
| parsing_rules | dict/string | No | Custom regex patterns for field extraction |

### Request Example

```python
# Basic text parsing
result = frappe.call(
    "sentra_core.api.create.create_document_from_unstructured_data",
    doctype="Contact",
    unstructured_data="""
    John Doe
    CEO, Tech Corp
    john.doe@techcorp.com
    +1-555-123-4567
    LinkedIn: linkedin.com/in/johndoe
    """,
    data_type="text"
)

# With custom parsing rules
parsing_rules = {
    "first_name": {"pattern": r"^(\w+)\s+\w+"},
    "last_name": {"pattern": r"^\w+\s+(\w+)"},
    "job_title": {"pattern": r"^.*?,\s*(.+)$"},
    "email_id": {"pattern": r"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})"},
    "mobile_no": {"pattern": r"(\+\d[\d\s\-]+)"}
}

result = frappe.call(
    "sentra_core.api.create.create_document_from_unstructured_data",
    doctype="Contact",
    unstructured_data=unstructured_text,
    data_type="text",
    parsing_rules=parsing_rules
)
```

### Response Example

```json
{
    "success": true,
    "message": "Data parsed successfully",
    "data": {
        "doctype": "Contact",
        "email_id": "john.doe@techcorp.com",
        "mobile_no": "+1-555-123-4567"
    },
    "require_confirmation": true
}
```

### Supported Data Types

1. **text**: Basic pattern matching for emails, phones, etc.
2. **json**: Direct JSON parsing
3. **xml**: XML parsing (basic support)

---

## 4. create_multiple_documents

Create multiple documents in a single transaction.

### Purpose
- Create multiple documents atomically (all succeed or all fail)
- Can create different DocTypes in one call
- Efficient for related document creation
- Returns detailed results for each document

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| documents | list | Yes | List of documents to create |

Each document in the list should have:
- `doctype`: The DocType to create
- `data`: The document data

### Request Example

```python
result = frappe.call(
    "sentra_core.api.create.create_multiple_documents",
    documents=[
        {
            "doctype": "Contact",
            "data": {
                "first_name": "Alice",
                "last_name": "Smith",
                "email_ids": [{"email_id": "alice@example.com", "is_primary": 1}]
            }
        },
        {
            "doctype": "Note",
            "data": {
                "title": "Meeting Notes",
                "content": "Discussion with Alice Smith",
                "public": 0
            }
        },
        {
            "doctype": "ToDo",
            "data": {
                "description": "Follow up with Alice",
                "status": "Open",
                "priority": "High"
            }
        }
    ]
)
```

### Response Example

```json
{
    "success": true,
    "message": "Created 3 documents successfully",
    "data": {
        "success_count": 3,
        "error_count": 0,
        "errors": [],
        "created_documents": [
            {"doctype": "Contact", "name": "Alice Smith"},
            {"doctype": "Note", "name": "NOTE-2024-00123"},
            {"doctype": "ToDo", "name": "TODO-2024-00456"}
        ]
    }
}
```

---

## 5. duplicate_document

Create a new document by duplicating an existing one.

### Purpose
- Copy an existing document with modifications
- Useful for creating similar records
- Preserves relationships and child tables
- Allows field overrides in the duplicate

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| doctype | string | Yes | The DocType to duplicate |
| source_name | string | Yes | Name of the source document |
| field_overrides | dict/string | No | Fields to change in the duplicate |

### Request Example

```python
# Duplicate a contact with changes
result = frappe.call(
    "sentra_core.api.create.duplicate_document",
    doctype="Contact",
    source_name="John Doe",
    field_overrides={
        "first_name": "Jane",
        "email_ids": [{"email_id": "jane.doe@example.com", "is_primary": 1}]
    }
)
```

### Response Example

```json
{
    "success": true,
    "message": "Contact duplicated successfully",
    "data": {
        "name": "Jane Doe",
        "first_name": "Jane",
        "last_name": "Doe",
        "email_id": "jane.doe@example.com",
        "mobile_no": "+919876543210",
        "contact_type": "Customer",
        "city": "Mumbai",
        "doctype": "Contact"
    }
}
```

---

## 6. get_document_template

Get a template for bulk upload with all available fields.

### Purpose
- Generate CSV/Excel templates for bulk upload
- Shows all importable fields with sample data
- Identifies required fields
- Helps users prepare data in correct format

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| doctype | string | Yes | The DocType to get template for |
| template_type | string | No | Format: "csv" or "json" (default: "csv") |

### Request Example

```python
# Get CSV template
result = frappe.call(
    "sentra_core.api.create.get_document_template",
    doctype="Contact",
    template_type="csv"
)

# Get JSON template
result = frappe.call(
    "sentra_core.api.create.get_document_template",
    doctype="Contact",
    template_type="json"
)
```

### Response Example (CSV)

```json
{
    "success": true,
    "data": {
        "content": "Zmlyc3RfbmFtZSxtaWRkbGVfbmFtZSxsYXN0X25hbWUsZW1haWxfaWQs...",
        "filename": "contact_template.csv",
        "fields": ["first_name", "middle_name", "last_name", "email_id", "mobile_no"],
        "field_labels": ["First Name", "Middle Name", "Last Name", "Email", "Mobile"]
    }
}
```

### Response Example (JSON)

```json
{
    "success": true,
    "data": {
        "fields": ["first_name", "middle_name", "last_name", "email_id", "mobile_no"],
        "sample": {
            "first_name": "Sample First Name",
            "middle_name": "Sample Middle Name",
            "last_name": "Sample Last Name",
            "email_id": "sample@example.com",
            "mobile_no": "Sample Mobile"
        },
        "required_fields": ["first_name"]
    }
}
```

---

## 7. get_doctype_create_schema

Get comprehensive field information for creating documents.

### Purpose
- Discover all fields available in a DocType
- Get field types, validation rules, and constraints
- Identify required, unique, and read-only fields
- Build dynamic forms based on schema

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| doctype | string | Yes | The DocType to get schema for |

### Request Example

```python
result = frappe.call(
    "sentra_core.api.create.get_doctype_create_schema",
    doctype="ToDo"
)
```

### Response Example

```json
{
    "success": true,
    "data": {
        "doctype": "ToDo",
        "fields": [
            {
                "fieldname": "description",
                "label": "Description",
                "fieldtype": "Text Editor",
                "reqd": 1,
                "unique": 0,
                "read_only": 0,
                "options": null,
                "default": null,
                "validation_pattern": null,
                "allowed_values": null
            },
            {
                "fieldname": "status",
                "label": "Status",
                "fieldtype": "Select",
                "reqd": 0,
                "unique": 0,
                "read_only": 0,
                "options": "Open\nClosed\nCancelled",
                "default": "Open",
                "allowed_values": ["Open", "Closed", "Cancelled"]
            },
            {
                "fieldname": "priority",
                "label": "Priority",
                "fieldtype": "Select",
                "reqd": 0,
                "unique": 0,
                "read_only": 0,
                "options": "High\nMedium\nLow",
                "default": "Medium",
                "allowed_values": ["High", "Medium", "Low"]
            },
            {
                "fieldname": "date",
                "label": "Due Date",
                "fieldtype": "Date",
                "reqd": 0,
                "unique": 0,
                "read_only": 0,
                "default": "Today"
            },
            {
                "fieldname": "allocated_to",
                "label": "Allocated To",
                "fieldtype": "Link",
                "reqd": 0,
                "unique": 0,
                "read_only": 0,
                "options": "User"
            }
        ],
        "required_fields": ["description"],
        "unique_fields": [],
        "read_only_fields": ["assignment_rule"],
        "link_fields": {
            "allocated_to": "User",
            "reference_type": "DocType",
            "assigned_by": "User"
        },
        "naming_rule": null,
        "title_field": "description",
        "custom_validations": [],
        "child_tables": []
    }
}
```

### Field Information Returned

- **fieldname**: Internal field name
- **label**: Display label
- **fieldtype**: Frappe field type (Data, Link, Select, etc.)
- **reqd**: Is field required (1/0)
- **unique**: Must be unique (1/0)
- **read_only**: Read-only field (1/0)
- **options**: For Select fields, contains allowed values
- **default**: Default value
- **validation_pattern**: Regex pattern for validation
- **allowed_values**: Array of allowed values for Select fields

---

## 8. validate_document_data

Pre-validate data before attempting to create a document.

### Purpose
- Validate data without creating the document
- Get detailed validation errors and warnings
- Check data types, required fields, and formats
- Useful for form validation before submission

### Parameters

| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| doctype | string | Yes | The DocType to validate against |
| data | dict/string | Yes | Data to validate |
| skip_required | boolean | No | Skip required field validation (default: False) |

### Request Example

```python
result = frappe.call(
    "sentra_core.api.create.validate_document_data",
    doctype="Contact",
    data={
        "first_name": "John",
        "email_id": "invalid-email",
        "mobile_no": "123"  # Too short
    }
)
```

### Response Example

```json
{
    "success": false,
    "message": "Validation failed",
    "errors": [
        "Email Address must be a valid email address",
        "Mobile must be a valid phone number",
        "At least one contact method is required: Email, Mobile Number, or Instagram ID"
    ],
    "warnings": [
        "Email Address is read-only and will be ignored"
    ],
    "data": {
        "errors_count": 3,
        "warnings_count": 1
    }
}
```

### Validation Checks Performed

1. **Required Fields**: Checks all mandatory fields
2. **Data Types**: Validates integers, floats, dates, etc.
3. **Format Validation**: Email, phone, date formats
4. **Select Options**: Validates against allowed values
5. **Length Constraints**: Maximum field lengths
6. **Read-only Fields**: Warns about fields that will be ignored
7. **Custom Patterns**: Uses field-specific validation patterns

---

## Common Use Cases

### 1. Creating a Contact with Full Validation

```python
# Step 1: Get schema to understand fields
schema = frappe.call("sentra_core.api.create.get_doctype_create_schema", doctype="Contact")

# Step 2: Validate data before submission
validation = frappe.call(
    "sentra_core.api.create.validate_document_data",
    doctype="Contact",
    data=contact_data
)

if not validation["success"]:
    # Handle validation errors
    print(validation["errors"])
else:
    # Step 3: Create the document
    result = frappe.call(
        "sentra_core.api.create.create_document",
        doctype="Contact",
        data=contact_data
    )
```

### 2. Bulk Import with Field Mapping

```python
# When CSV columns don't match field names
field_mapping = {
    "Full Name": "first_name",
    "Email Address": "email_id",
    "Phone Number": "mobile_no",
    "Type": "contact_type"
}

result = frappe.call(
    "sentra_core.api.create.bulk_upload_documents",
    doctype="Contact",
    file_content=csv_base64,
    file_type="csv",
    field_mapping=field_mapping
)
```

### 3. AI Bot Creating Documents

```python
# AI bot with messy data
ai_data = {
    "description": "Complete quarterly report",
    "priority": "high",  # lowercase - will be validated
    "status": "open",    # lowercase - will be validated
    "date": "31/12/2024",  # non-standard format - will be converted
    "allocated_to": "john@example.com"  # email instead of username
}

# The API will validate and provide clear errors
result = frappe.call(
    "sentra_core.api.create.create_document",
    doctype="ToDo",
    data=ai_data
)

# Response will include validation errors:
# - "Status must be one of: Open, Closed, Cancelled"
# - "Priority must be one of: High, Medium, Low"
```

### 4. Creating Related Documents

```python
# Create a Contact and CRM Lead together
documents = [
    {
        "doctype": "Contact",
        "data": {
            "first_name": "New",
            "last_name": "Customer",
            "email_ids": [{"email_id": "new@customer.com", "is_primary": 1}]
        }
    },
    {
        "doctype": "CRM Lead",
        "data": {
            "link_to_contact": "New Customer",  # Use the contact name
            "status": "New",
            "source": "Website",
            "lead_owner": "Administrator"
        }
    }
]

result = frappe.call(
    "sentra_core.api.create.create_multiple_documents",
    documents=documents
)
```

---

## Error Handling

### Common Error Types

1. **Validation Errors**
   - Missing required fields
   - Invalid field values
   - Format violations

2. **Permission Errors**
   - User lacks create permission
   - DocType restrictions

3. **Data Type Errors**
   - Invalid data types
   - Conversion failures

4. **Business Logic Errors**
   - Custom validation failures
   - Workflow restrictions

### Error Response Format

```json
{
    "success": false,
    "message": "Main error message",
    "validation_errors": [
        "Field-specific error 1",
        "Field-specific error 2"
    ],
    "validation_warnings": [
        "Warning 1",
        "Warning 2"
    ],
    "data": null
}
```

---

## Best Practices

1. **Always Get Schema First**
   - Use `get_doctype_create_schema` to understand available fields
   - Build dynamic forms based on schema

2. **Validate Before Creating**
   - Use `validate_document_data` for client-side validation
   - Provide immediate feedback to users

3. **Handle Child Tables Properly**
   - Child tables should be arrays of objects
   - Each child record is a dictionary

4. **Use Field Mapping for Imports**
   - Map CSV columns to field names
   - Prevents import failures due to naming mismatches

5. **Leverage Type Conversion**
   - API handles common conversions automatically
   - Send data in convenient formats

6. **Batch Operations When Possible**
   - Use `bulk_upload_documents` for multiple similar documents
   - Use `create_multiple_documents` for related documents

---

## Appendix: Supported Field Types

| Field Type | Validation | Type Conversion |
|------------|------------|-----------------|
| Data | String validation | Trim whitespace |
| Int | Integer validation | String → Integer |
| Float | Float validation | String → Float |
| Currency | Float validation | String → Float |
| Percent | Float validation | String → Float |
| Check | Boolean validation | "yes"/"true"/"1" → 1, "no"/"false"/"0" → 0 |
| Date | Date format validation | Multiple formats → YYYY-MM-DD |
| Datetime | Datetime format validation | String → Datetime |
| Time | Time format validation | String → HH:MM:SS |
| Select | Options validation | Case-sensitive match |
| Link | String validation | No conversion |
| Table | Array validation | Must be array of objects |
| Text Editor | String validation | HTML allowed |
| Small/Long Text | String validation | No conversion |

---

## Version History

- **v1.0.0** (2024-12-20): Initial release with all core functions