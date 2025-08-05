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
def create_document(doctype: str, data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Create a single document of any doctype
    
    Args:
        doctype: The DocType to create
        data: Document data including all fields
        
    Returns:
        Created document
    """
    try:
        # Parse data if it's a string
        if isinstance(data, str):
            data = json.loads(data)
            
        # Create document
        doc = frappe.get_doc({
            "doctype": doctype,
            **data
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
        return {
            "success": False,
            "message": str(e)
        }


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
def create_document_from_unstructured_data(
    doctype: str,
    unstructured_data: str,
    data_type: str = "text",
    parsing_rules: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Create document from unstructured data using AI parsing or rule-based extraction
    
    Args:
        doctype: The DocType to create
        unstructured_data: Raw text, business card info, email signature, etc.
        data_type: Type of data (text, business_card, email_signature, json, xml)
        parsing_rules: Optional rules for parsing specific fields
        
    Returns:
        Created document or parsed data for review
    """
    try:
        parsed_data = {
            "doctype": doctype
        }
        
        # Parse based on data type
        if data_type == "json":
            try:
                parsed_data.update(json.loads(unstructured_data))
            except:
                pass
                
        elif data_type == "xml":
            # Basic XML parsing could be added here
            pass
            
        else:
            # Basic text parsing with common patterns
            lines = unstructured_data.strip().split('\n')
            
            # Get doctype meta to understand available fields
            meta = frappe.get_meta(doctype)
            field_map = {field.fieldname: field for field in meta.fields}
            
            # Apply parsing rules if provided
            if parsing_rules and isinstance(parsing_rules, str):
                parsing_rules = json.loads(parsing_rules)
            
            # Common patterns
            for line in lines:
                line = line.strip()
                
                # Email pattern
                if '@' in line:
                    # Look for email fields
                    email_fields = [f for f in field_map.keys() if 'email' in f.lower()]
                    if email_fields:
                        parsed_data[email_fields[0]] = line
                    elif 'email_id' in field_map:
                        parsed_data['email_id'] = line
                            
                # Phone pattern
                elif (line.startswith('+') or any(char.isdigit() for char in line)) and len([char for char in line if char.isdigit()]) >= 10:
                    # Look for mobile/phone fields
                    mobile_fields = [f for f in field_map.keys() if any(term in f.lower() for term in ['mobile', 'phone'])]
                    if mobile_fields:
                        # Prefer mobile_no over other fields
                        if 'mobile_no' in mobile_fields:
                            parsed_data['mobile_no'] = line
                        else:
                            parsed_data[mobile_fields[0]] = line
                            
                # Apply custom parsing rules
                if parsing_rules:
                    for field, rule in parsing_rules.items():
                        if isinstance(rule, dict) and "pattern" in rule:
                            import re
                            match = re.search(rule["pattern"], line)
                            if match:
                                parsed_data[field] = match.group(1) if match.groups() else match.group(0)
                                
        return {
            "success": True,
            "message": _("Data parsed successfully"),
            "data": parsed_data,
            "require_confirmation": True  # Frontend should confirm before creating
        }
    except Exception as e:
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