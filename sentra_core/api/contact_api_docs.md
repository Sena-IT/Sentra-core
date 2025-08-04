# Contact API Documentation

## Base URL
```
/api/method/sentra_core.api.contact.{method_name}
```

## Authentication
All API endpoints require Frappe authentication (session or token).

## API Endpoints

### 1. CREATE Operations

#### Create Single Contact
```http
POST /api/method/sentra_core.api.contact.create_contact
```

**Request Body:**
```json
{
    "data": {
        "first_name": "John",
        "last_name": "Doe",
        "email_id": "john.doe@example.com",
        "mobile_no": "+91-9876543210",
        "contact_type": "Customer",
        "contact_category": "Individual",
        "city": "Mumbai",
        "state": "Maharashtra",
        "gstin": "27AAPFU0939F1ZV"
    }
}
```

**Response:**
```json
{
    "success": true,
    "message": "Contact created successfully",
    "data": {
        "name": "CONT-2024-00001",
        "full_name": "John Doe",
        ...
    }
}
```

#### Bulk Upload Contacts
```http
POST /api/method/sentra_core.api.contact.bulk_upload_contacts
```

**Request Body:**
```json
{
    "file_content": "base64_encoded_csv_content",
    "file_type": "csv"  // or "xlsx"
}
```

**CSV Format:**
```csv
first_name,last_name,email_id,mobile_no,contact_type,city
John,Doe,john@example.com,9876543210,Customer,Mumbai
Jane,Smith,jane@example.com,9876543211,Vendor,Delhi
```

#### AI-Assisted Contact Creation
```http
POST /api/method/sentra_core.api.contact.create_contact_from_ai
```

**Request Body:**
```json
{
    "unstructured_data": "John Doe\nSales Manager\nABC Corp\njohn.doe@abccorp.com\n+91-9876543210",
    "data_type": "business_card"
}
```

### 2. READ Operations

#### Get Contacts List
```http
GET /api/method/sentra_core.api.contact.get_contacts
```

**Query Parameters:**
- `filters`: JSON object for filtering (e.g., `{"contact_type": "Customer"}`)
- `fields`: Array of fields to return
- `order_by`: Sort order (default: "modified desc")
- `page`: Page number (default: 1)
- `page_size`: Items per page (default: 20)
- `search_text`: Search across name, email, phone

**Example Request:**
```
GET /api/method/sentra_core.api.contact.get_contacts?filters={"city":"Mumbai"}&page=1&page_size=20&search_text=john
```

#### Get Contact Detail
```http
GET /api/method/sentra_core.api.contact.get_contact_detail
```

**Query Parameters:**
- `contact_name`: Contact ID (e.g., "CONT-2024-00001")

**Response includes:**
- Complete contact information
- Linked documents
- Recent communications

#### AI Natural Language Search
```http
GET /api/method/sentra_core.api.contact.search_contacts_ai
```

**Query Parameters:**
- `query`: Natural language query (e.g., "all vendors in Mumbai")

### 3. UPDATE Operations

#### Update Single Contact
```http
POST /api/method/sentra_core.api.contact.update_contact
```

**Request Body:**
```json
{
    "contact_name": "CONT-2024-00001",
    "data": {
        "mobile_no": "+91-9876543999",
        "city": "Pune"
    }
}
```

#### Export Contacts
```http
GET /api/method/sentra_core.api.contact.export_contacts
```

**Query Parameters:**
- `filters`: JSON object for filtering
- `format`: Export format ("csv" or "xlsx")

**Response:**
```json
{
    "success": true,
    "data": {
        "content": "base64_encoded_content",
        "filename": "contacts_20240115_143022.csv",
        "format": "csv"
    }
}
```

#### Bulk Update Contacts
```http
POST /api/method/sentra_core.api.contact.bulk_update_contacts
```

**Request Body:**
```json
{
    "updates": [
        {
            "contact_name": "CONT-2024-00001",
            "city": "Bangalore",
            "state": "Karnataka"
        },
        {
            "contact_name": "CONT-2024-00002",
            "contact_type": "Vendor"
        }
    ]
}
```

### 4. DELETE Operations

#### Delete Single Contact
```http
POST /api/method/sentra_core.api.contact.delete_contact
```

**Request Body:**
```json
{
    "contact_name": "CONT-2024-00001"
}
```

#### Bulk Delete Contacts
```http
POST /api/method/sentra_core.api.contact.bulk_delete_contacts
```

**Request Body:**
```json
{
    "contact_names": ["CONT-2024-00001", "CONT-2024-00002", "CONT-2024-00003"]
}
```

#### AI-Assisted Delete
```http
POST /api/method/sentra_core.api.contact.delete_contacts_ai
```

**Request Body:**
```json
{
    "query": "delete all inactive contacts from 2020",
    "dry_run": true  // Set to false to actually delete
}
```

### 5. UTILITY Operations

#### Get Contact Metadata
```http
GET /api/method/sentra_core.api.contact.get_contact_meta
```

Returns field definitions, types, and validation rules.

## Validation Rules

### Contact Type Specific Validations

#### Employee Contacts
- `employee_code`: Required and unique
- `date_of_joining`: Required
- Employee must be 18+ years at joining date
- Cannot be their own manager

#### Vendor Contacts
- `vendor_type`: Required
- GSTIN recommended for Airline, Hotel, Transport vendors

### Field Validations

#### GSTIN
- Format: 15 characters
- Pattern: `^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$`
- Auto-converted to uppercase

#### Mobile Number
- Indian format: 10 digits starting with 6-9
- Optional +91 prefix
- Pattern: `^(\+91[-.\s]?)?[6-9]\d{9}$`

#### Email
- Standard email validation
- Warning on duplicate emails

## Error Handling

All APIs return consistent error responses:

```json
{
    "success": false,
    "message": "Error description"
}
```

For bulk operations:
```json
{
    "success": true,
    "message": "Processed X items",
    "data": {
        "success_count": 8,
        "error_count": 2,
        "errors": [
            {
                "row": 3,
                "error": "Invalid GSTIN format"
            }
        ]
    }
}
```

## Frontend Integration Examples

### Vue.js with Frappe UI

```javascript
// Create contact
const result = await $fetch('/api/method/sentra_core.api.contact.create_contact', {
    method: 'POST',
    body: {
        data: {
            first_name: 'John',
            last_name: 'Doe',
            email_id: 'john@example.com'
        }
    }
});

// Get contacts with pagination
const contacts = await $fetch('/api/method/sentra_core.api.contact.get_contacts', {
    params: {
        page: 1,
        page_size: 20,
        filters: JSON.stringify({ contact_type: 'Customer' })
    }
});
```

### File Upload Example

```javascript
// Convert file to base64
const fileToBase64 = (file) => {
    return new Promise((resolve, reject) => {
        const reader = new FileReader();
        reader.readAsDataURL(file);
        reader.onload = () => resolve(reader.result.split(',')[1]);
        reader.onerror = reject;
    });
};

// Upload CSV
const base64Content = await fileToBase64(csvFile);
const result = await $fetch('/api/method/sentra_core.api.contact.bulk_upload_contacts', {
    method: 'POST',
    body: {
        file_content: base64Content,
        file_type: 'csv'
    }
});
```

## Rate Limiting

- Bulk operations are limited to 1000 records per request
- Export operations are limited to 10000 records
- AI operations have a 5 second timeout

## Notes for Frontend Team

1. **Modal Forms**: Use `get_contact_meta` to dynamically build forms
2. **Validation**: Client-side validation should match server rules
3. **Error Display**: Show field-specific errors from validation
4. **Pagination**: Always use pagination for list views
5. **Search**: Debounce search input (300ms recommended)
6. **File Uploads**: Show progress for large files
7. **AI Features**: Show preview/confirmation before executing