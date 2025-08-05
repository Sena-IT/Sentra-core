import frappe
from frappe import _
from typing import Dict, List, Optional, Any
import json
import csv
import io
import base64
import pandas as pd
from datetime import datetime


@frappe.whitelist()
def create_document(doctype: str, data: Dict[str, Any], skip_validation: bool = False) -> Dict[str, Any]:
    """
    Create a single document of any doctype with automatic validation
    
    Args:
        doctype: The DocType to create
        data: Document data including all fields
        skip_validation: Skip pre-validation (use Frappe's validation only)
        
    Returns:
        Created document or validation errors
    """
    try:
        # Parse data if it's a string
        if isinstance(data, str):
            data = json.loads(data)
        
        # Skip validation if requested (for backward compatibility)
        if not skip_validation:
            # Get schema and validate
            validation_result = validate_document_data(doctype, data)
            
            if not validation_result["success"]:
                return {
                    "success": False,
                    "message": "Validation failed",
                    "validation_errors": validation_result["errors"],
                    "validation_warnings": validation_result["warnings"],
                    "data": None
                }
            
            # Process the data based on schema to handle type conversions and clean data
            schema = get_doctype_create_schema(doctype)
            if schema["success"]:
                cleaned_data = _clean_and_convert_data(data, schema["data"]["fields"])
            else:
                cleaned_data = data
        else:
            cleaned_data = data
            
        # Create document with cleaned data
        doc = frappe.get_doc({
            "doctype": doctype,
            **cleaned_data
        })
        
        doc.insert()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _(f"{doctype} created successfully"),
            "data": doc.as_dict()
        }
    except Exception as e:
        frappe.db.rollback()
        
        # Try to extract more specific error information
        error_message = str(e)
        validation_errors = []
        
        # Parse common Frappe validation errors
        if "Missing mandatory fields" in error_message:
            # Extract field names from error
            import re
            fields = re.findall(r'\[(.*?)\]', error_message)
            if fields:
                validation_errors = [f"{field} is required" for field in fields[0].split(", ")]
        elif "already exists" in error_message:
            validation_errors = ["A record with this value already exists"]
        elif "does not exist" in error_message:
            validation_errors = [error_message]
            
        return {
            "success": False,
            "message": error_message,
            "validation_errors": validation_errors,
            "data": None
        }


def _clean_and_convert_data(data: Dict[str, Any], fields: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Clean and convert data based on field types
    
    Args:
        data: Raw input data
        fields: Field definitions from schema
        
    Returns:
        Cleaned data with proper types
    """
    cleaned = {}
    fields_map = {f["fieldname"]: f for f in fields}
    
    for key, value in data.items():
        if key in fields_map:
            field = fields_map[key]
            
            # Skip read-only fields
            if field.get("read_only"):
                continue
                
            # Skip None values
            if value is None:
                continue
                
            # Type conversion
            try:
                if field["fieldtype"] == "Int" and value is not None:
                    cleaned[key] = int(value)
                elif field["fieldtype"] in ["Float", "Currency"] and value is not None:
                    cleaned[key] = float(value)
                elif field["fieldtype"] == "Check":
                    # Handle various boolean representations
                    if isinstance(value, str):
                        cleaned[key] = 1 if value.lower() in ["true", "1", "yes", "on"] else 0
                    else:
                        cleaned[key] = 1 if value else 0
                elif field["fieldtype"] == "Date" and isinstance(value, str):
                    # Validate date format
                    import re
                    if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                        cleaned[key] = value
                    else:
                        # Try to parse common date formats
                        from datetime import datetime
                        for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
                            try:
                                date_obj = datetime.strptime(value, fmt)
                                cleaned[key] = date_obj.strftime("%Y-%m-%d")
                                break
                            except:
                                continue
                        else:
                            cleaned[key] = value  # Let Frappe handle the error
                else:
                    # For all other types, keep as is
                    cleaned[key] = value
            except (ValueError, TypeError):
                # If conversion fails, keep original value and let Frappe validate
                cleaned[key] = value
        else:
            # Include fields not in schema (might be valid system fields)
            cleaned[key] = value
            
    return cleaned


@frappe.whitelist()
def bulk_upload_documents(
    doctype: str,
    file_content: str,
    file_type: str = "csv",
    field_mapping: Optional[Dict[str, str]] = None
) -> Dict[str, Any]:
    """
    Bulk upload documents from CSV/Excel
    
    Args:
        doctype: The DocType to create documents for
        file_content: Base64 encoded file content
        file_type: Type of file (csv, xlsx)
        field_mapping: Optional mapping of CSV columns to doctype fields
        
    Returns:
        Upload results with success/failure counts
    """
    try:
        # Decode file content
        decoded = base64.b64decode(file_content)
        
        # Parse based on file type
        if file_type == "csv":
            df = pd.read_csv(io.StringIO(decoded.decode('utf-8')))
        else:
            df = pd.read_excel(io.BytesIO(decoded))
            
        # Apply field mapping if provided
        if field_mapping and isinstance(field_mapping, str):
            field_mapping = json.loads(field_mapping)
        if field_mapping:
            df = df.rename(columns=field_mapping)
            
        success_count = 0
        errors = []
        created_documents = []
        
        for idx, row in df.iterrows():
            try:
                doc_data = row.to_dict()
                # Remove NaN values and handle special fields
                cleaned_data = {}
                for k, v in doc_data.items():
                    if pd.notna(v):
                        # Convert phone/mobile fields to strings
                        if any(term in k.lower() for term in ['phone', 'mobile', 'contact_no']):
                            cleaned_data[k] = str(v)
                        else:
                            cleaned_data[k] = v
                
                doc = frappe.get_doc({
                    "doctype": doctype,
                    **cleaned_data
                })
                doc.insert()
                success_count += 1
                created_documents.append(doc.name)
            except Exception as e:
                errors.append({
                    "row": idx + 2,  # +2 for header and 0-index
                    "error": str(e),
                    "data": doc_data
                })
                
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _(f"Uploaded {success_count} {doctype} documents successfully"),
            "data": {
                "success_count": success_count,
                "error_count": len(errors),
                "errors": errors[:10],  # Return first 10 errors
                "created_documents": created_documents[:100]  # Return first 100 document names
            }
        }
    except Exception as e:
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def create_multiple_documents(documents: List[Dict[str, Any]]) -> Dict[str, Any]:
    """
    Create multiple documents in a single transaction
    
    Args:
        documents: List of documents to create, each with doctype and data
        
    Returns:
        Creation results
    """
    try:
        if isinstance(documents, str):
            documents = json.loads(documents)
            
        success_count = 0
        errors = []
        created_documents = []
        
        for idx, doc_info in enumerate(documents):
            try:
                doctype = doc_info.get("doctype")
                data = doc_info.get("data", {})
                
                if not doctype:
                    raise ValueError("doctype is required for each document")
                    
                doc = frappe.get_doc({
                    "doctype": doctype,
                    **data
                })
                doc.insert()
                success_count += 1
                created_documents.append({
                    "doctype": doctype,
                    "name": doc.name
                })
            except Exception as e:
                errors.append({
                    "index": idx,
                    "doctype": doctype,
                    "error": str(e)
                })
                
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _(f"Created {success_count} documents successfully"),
            "data": {
                "success_count": success_count,
                "error_count": len(errors),
                "errors": errors,
                "created_documents": created_documents
            }
        }
    except Exception as e:
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def duplicate_document(
    doctype: str,
    source_name: str,
    field_overrides: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create a new document by duplicating an existing one
    
    Args:
        doctype: The DocType to duplicate
        source_name: Name of the source document
        field_overrides: Fields to override in the duplicate
        
    Returns:
        Created duplicate document
    """
    try:
        # Get source document
        source_doc = frappe.get_doc(doctype, source_name)
        
        # Create duplicate
        new_doc = frappe.copy_doc(source_doc)
        
        # Apply overrides
        if field_overrides:
            if isinstance(field_overrides, str):
                field_overrides = json.loads(field_overrides)
            for field, value in field_overrides.items():
                if hasattr(new_doc, field):
                    setattr(new_doc, field, value)
                    
        new_doc.insert()
        frappe.db.commit()
        
        return {
            "success": True,
            "message": _(f"{doctype} duplicated successfully"),
            "data": new_doc.as_dict()
        }
    except Exception as e:
        frappe.db.rollback()
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_doctype_create_schema(doctype: str) -> Dict[str, Any]:
    """
    Get comprehensive schema information for creating documents
    
    Args:
        doctype: The DocType to get schema for
        
    Returns:
        Complete field information including validation rules
    """
    try:
        meta = frappe.get_meta(doctype)
        
        fields_info = []
        for field in meta.fields:
            if field.fieldtype in ["Section Break", "Column Break", "HTML", "Table"]:
                continue
                
            field_info = {
                "fieldname": field.fieldname,
                "label": field.label,
                "fieldtype": field.fieldtype,
                "reqd": field.reqd,
                "unique": field.unique,
                "read_only": field.read_only,
                "options": field.options,  # For Link fields, this is the linked DocType
                "default": field.default,
                "max_length": getattr(field, 'length', None),
                "precision": getattr(field, 'precision', None),
                "validation_pattern": None,
                "allowed_values": None
            }
            
            # Add validation patterns for common types
            if field.fieldtype == "Email":
                field_info["validation_pattern"] = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            elif field.fieldtype == "Phone":
                field_info["validation_pattern"] = r"^[\d\s\-\+\(\)]+$"
            elif field.fieldtype == "Int":
                field_info["validation_pattern"] = r"^\d+$"
            elif field.fieldtype == "Float" or field.fieldtype == "Currency":
                field_info["validation_pattern"] = r"^\d+\.?\d*$"
            
            # For Select fields, get the options
            if field.fieldtype == "Select" and field.options:
                field_info["allowed_values"] = [opt.strip() for opt in field.options.split("\n") if opt.strip()]
            
            # Add any custom validation from field
            if hasattr(field, 'mandatory_depends_on'):
                field_info["mandatory_depends_on"] = field.mandatory_depends_on
            if hasattr(field, 'depends_on'):
                field_info["depends_on"] = field.depends_on
                
            fields_info.append(field_info)
        
        # Get any custom validation methods
        custom_validations = []
        try:
            doc_module = frappe.get_module(f"{meta.module}.doctype.{frappe.scrub(doctype)}.{frappe.scrub(doctype)}")
            if hasattr(doc_module, doctype):
                doc_class = getattr(doc_module, doctype)
                if hasattr(doc_class, 'validate'):
                    custom_validations.append("Custom validate method exists")
        except:
            pass
        
        return {
            "success": True,
            "data": {
                "doctype": doctype,
                "fields": fields_info,
                "required_fields": [f["fieldname"] for f in fields_info if f["reqd"]],
                "unique_fields": [f["fieldname"] for f in fields_info if f["unique"]],
                "read_only_fields": [f["fieldname"] for f in fields_info if f["read_only"]],
                "link_fields": {
                    f["fieldname"]: f["options"] 
                    for f in fields_info 
                    if f["fieldtype"] == "Link"
                },
                "naming_rule": meta.naming_rule,
                "title_field": meta.title_field,
                "custom_validations": custom_validations,
                "child_tables": [
                    {
                        "fieldname": f.fieldname,
                        "label": f.label,
                        "child_doctype": f.options
                    }
                    for f in meta.fields 
                    if f.fieldtype == "Table"
                ]
            }
        }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def validate_document_data(doctype: str, data: Dict[str, Any], skip_required: bool = False) -> Dict[str, Any]:
    """
    Pre-validate document data before creation
    
    Args:
        doctype: The DocType to validate against
        data: The data to validate
        skip_required: Skip required field validation (useful for drafts)
        
    Returns:
        Validation results with specific errors
    """
    try:
        if isinstance(data, str):
            data = json.loads(data)
            
        errors = []
        warnings = []
        
        # Get schema
        schema = get_doctype_create_schema(doctype)
        if not schema["success"]:
            return schema
            
        fields_map = {f["fieldname"]: f for f in schema["data"]["fields"]}
        
        # Check for unknown fields
        for fieldname in data.keys():
            if fieldname not in fields_map and fieldname not in ["doctype"]:
                warnings.append(f"Unknown field: {fieldname}")
        
        # Validate each field
        for field_info in schema["data"]["fields"]:
            fieldname = field_info["fieldname"]
            value = data.get(fieldname)
            
            # Required field check
            if not skip_required and field_info["reqd"]:
                # Check for empty values more thoroughly
                if value is None or value == "":
                    errors.append(f"{field_info['label']} is required")
                    continue
                # For string fields, also check whitespace-only
                if isinstance(value, str) and not value.strip():
                    errors.append(f"{field_info['label']} cannot be empty or whitespace only")
                    continue
                
            # Skip if no value provided
            if value is None:
                continue
                
            # Read-only check
            if field_info["read_only"]:
                warnings.append(f"{field_info['label']} is read-only and will be ignored")
                continue
            
            # Type validation
            if field_info["fieldtype"] == "Int":
                try:
                    int(value)
                except:
                    errors.append(f"{field_info['label']} must be an integer, got: {type(value).__name__}")
                    
            elif field_info["fieldtype"] in ["Float", "Currency", "Percent"]:
                try:
                    float(value)
                except:
                    errors.append(f"{field_info['label']} must be a number, got: {type(value).__name__}")
                    
            elif field_info["fieldtype"] == "Check":
                # Accept various boolean representations
                valid_values = [0, 1, True, False, "0", "1", "true", "false", "True", "False", "yes", "no", "on", "off"]
                if value not in valid_values:
                    errors.append(f"{field_info['label']} must be a boolean value (0/1, true/false, yes/no)")
                    
            elif field_info["fieldtype"] == "Date":
                import re
                from datetime import datetime
                valid_date = False
                
                # Check standard format
                if re.match(r'^\d{4}-\d{2}-\d{2}$', str(value)):
                    valid_date = True
                else:
                    # Try parsing common formats
                    for fmt in ["%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y", "%Y/%m/%d"]:
                        try:
                            datetime.strptime(str(value), fmt)
                            valid_date = True
                            warnings.append(f"{field_info['label']} will be converted to YYYY-MM-DD format")
                            break
                        except:
                            continue
                
                if not valid_date:
                    errors.append(f"{field_info['label']} must be a valid date (YYYY-MM-DD format preferred)")
                    
            elif field_info["fieldtype"] == "Datetime":
                import re
                if not re.match(r'^\d{4}-\d{2}-\d{2}\s\d{2}:\d{2}:\d{2}', str(value)):
                    errors.append(f"{field_info['label']} must be in YYYY-MM-DD HH:MM:SS format")
                    
            elif field_info["fieldtype"] == "Time":
                import re
                if not re.match(r'^\d{2}:\d{2}:\d{2}', str(value)):
                    errors.append(f"{field_info['label']} must be in HH:MM:SS format")
                    
            elif field_info["fieldtype"] == "Select" and field_info.get("allowed_values"):
                if value not in field_info["allowed_values"]:
                    errors.append(f"{field_info['label']} must be one of: {', '.join(field_info['allowed_values'])}")
                    
            elif field_info["fieldtype"] == "Link":
                # Check if it's a valid string (link validation happens in Frappe)
                if not isinstance(value, str) or not value.strip():
                    errors.append(f"{field_info['label']} must be a valid {field_info.get('options', 'reference')}")
                else:
                    # Could add check if linked document exists
                    warnings.append(f"{field_info['label']} link validity will be checked during creation")
                    
            elif field_info["fieldtype"] == "Data" and field_info.get("options") == "Email":
                # Email validation
                import re
                email_pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
                if not re.match(email_pattern, str(value)):
                    errors.append(f"{field_info['label']} must be a valid email address")
                    
            elif field_info["fieldtype"] == "Data" and field_info.get("options") == "Phone":
                # Phone validation
                import re
                phone_pattern = r'^[\d\s\-\+\(\)]{7,}$'
                if not re.match(phone_pattern, str(value)):
                    errors.append(f"{field_info['label']} must be a valid phone number")
                    
            elif field_info["fieldtype"] in ["Small Text", "Text", "Long Text", "Text Editor"]:
                # Text fields - check if string
                if not isinstance(value, str):
                    warnings.append(f"{field_info['label']} will be converted to string")
                    
            elif field_info["fieldtype"] == "Table":
                # Child table validation
                if not isinstance(value, list):
                    errors.append(f"{field_info['label']} must be a list of child records")
                else:
                    # Basic check for child records
                    for idx, child in enumerate(value):
                        if not isinstance(child, dict):
                            errors.append(f"{field_info['label']}[{idx}] must be a dictionary")
                            
            # Length validation for string fields
            if field_info.get("max_length") and isinstance(value, str):
                if len(value) > field_info["max_length"]:
                    errors.append(f"{field_info['label']} exceeds maximum length of {field_info['max_length']}")
                    
            # Pattern validation
            if field_info.get("validation_pattern") and isinstance(value, str):
                import re
                if not re.match(field_info["validation_pattern"], value):
                    errors.append(f"{field_info['label']} has invalid format")
        
        return {
            "success": len(errors) == 0,
            "message": "Validation passed" if len(errors) == 0 else "Validation failed",
            "errors": errors,
            "warnings": warnings,
            "data": {
                "errors_count": len(errors),
                "warnings_count": len(warnings)
            }
        }
        
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }


@frappe.whitelist()
def get_document_template(doctype: str, template_type: str = "csv") -> Dict[str, Any]:
    """
    Get a template for bulk upload
    
    Args:
        doctype: The DocType to get template for
        template_type: Type of template (csv, xlsx, json)
        
    Returns:
        Template content or structure
    """
    try:
        meta = frappe.get_meta(doctype)
        
        # Get importable fields
        fields = []
        field_labels = []
        sample_data = {}
        
        for field in meta.fields:
            if field.fieldtype not in ["Section Break", "Column Break", "HTML", "Table"] and not field.read_only:
                fields.append(field.fieldname)
                field_labels.append(field.label)
                
                # Add sample data based on field type
                if field.fieldtype in ["Data", "Long Text", "Text", "Small Text"]:
                    sample_data[field.fieldname] = f"Sample {field.label}"
                elif field.fieldtype in ["Int", "Float", "Currency"]:
                    sample_data[field.fieldname] = 0
                elif field.fieldtype == "Date":
                    sample_data[field.fieldname] = "2024-01-01"
                elif field.fieldtype == "Check":
                    sample_data[field.fieldname] = 0
                elif field.fieldtype == "Link":
                    sample_data[field.fieldname] = f"Valid {field.options}"
                    
        if template_type == "json":
            return {
                "success": True,
                "data": {
                    "fields": fields,
                    "sample": sample_data,
                    "required_fields": [f.fieldname for f in meta.fields if f.reqd]
                }
            }
        else:
            # Generate CSV content
            output = io.StringIO()
            writer = csv.DictWriter(output, fieldnames=fields)
            writer.writeheader()
            writer.writerow(sample_data)
            
            return {
                "success": True,
                "data": {
                    "content": base64.b64encode(output.getvalue().encode()).decode(),
                    "filename": f"{doctype.lower()}_template.csv",
                    "fields": fields,
                    "field_labels": field_labels
                }
            }
    except Exception as e:
        return {
            "success": False,
            "message": str(e)
        }