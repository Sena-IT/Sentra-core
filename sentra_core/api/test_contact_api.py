#!/usr/bin/env python
"""
Test script for Contact APIs
Run with: bench execute sentra_core.api.test_contact_api.test_all
"""

import frappe
from sentra_core.api import contact
import json

def test_all():
    """Run all contact API tests"""
    print("Testing Contact APIs...")
    
    # Test 1: Create Contact
    print("\n1. Testing Create Contact:")
    result = contact.create_contact({
        "first_name": "Test",
        "last_name": "User",
        "email_id": "test.user@example.com",
        "mobile_no": "9876543210",
        "contact_type": "Customer",
        "city": "Mumbai"
    })
    print(f"Create Result: {result['success']} - {result.get('message', '')}")
    
    if result['success']:
        contact_name = result['data']['name']
        print(f"Created Contact: {contact_name}")
        
        # Test 2: Get Contact Detail
        print("\n2. Testing Get Contact Detail:")
        detail_result = contact.get_contact_detail(contact_name)
        print(f"Detail Result: {detail_result['success']}")
        if detail_result['success']:
            print(f"Contact Name: {detail_result['data']['full_name']}")
        
        # Test 3: Update Contact
        print("\n3. Testing Update Contact:")
        update_result = contact.update_contact(contact_name, {
            "city": "Delhi",
            "state": "Delhi"
        })
        print(f"Update Result: {update_result['success']} - {update_result.get('message', '')}")
        
        # Test 4: Get Contacts List
        print("\n4. Testing Get Contacts List:")
        list_result = contact.get_contacts(
            filters={"contact_type": "Customer"},
            page=1,
            page_size=10
        )
        print(f"List Result: {list_result['success']}")
        if list_result['success']:
            print(f"Total Contacts: {list_result['data']['pagination']['total']}")
            print(f"Returned: {len(list_result['data']['contacts'])} contacts")
        
        # Test 5: Search with AI
        print("\n5. Testing AI Search:")
        search_result = contact.search_contacts_ai("customers in delhi")
        print(f"Search Result: {search_result['success']}")
        if search_result['success']:
            print(f"Found: {len(search_result['data']['contacts'])} contacts")
        
        # Test 6: Get Metadata
        print("\n6. Testing Get Metadata:")
        meta_result = contact.get_contact_meta()
        print(f"Meta Result: {meta_result['success']}")
        if meta_result['success']:
            print(f"Total Fields: {len(meta_result['data']['fields'])}")
        
        # Test 7: Delete Contact
        print("\n7. Testing Delete Contact:")
        delete_result = contact.delete_contact(contact_name)
        print(f"Delete Result: {delete_result['success']} - {delete_result.get('message', '')}")
    
    print("\n✅ All tests completed!")

def test_validation():
    """Test validation rules"""
    print("Testing Contact Validation Rules...")
    
    # Test GSTIN validation
    print("\n1. Testing GSTIN Validation:")
    try:
        result = contact.create_contact({
            "first_name": "Invalid GSTIN Test",
            "gstin": "INVALID123"
        })
        print("❌ GSTIN validation failed - invalid format accepted")
    except Exception as e:
        print(f"✅ GSTIN validation working - {str(e)}")
    
    # Test Employee validation
    print("\n2. Testing Employee Validation:")
    try:
        result = contact.create_contact({
            "first_name": "Employee Test",
            "contact_type": "Employee"
            # Missing required employee_code
        })
        print("❌ Employee validation failed - missing employee_code accepted")
    except Exception as e:
        print(f"✅ Employee validation working - {str(e)}")
    
    # Test Phone validation
    print("\n3. Testing Phone Validation:")
    try:
        result = contact.create_contact({
            "first_name": "Phone Test",
            "mobile_no": "123"  # Invalid phone
        })
        print("❌ Phone validation failed - invalid number accepted")
    except Exception as e:
        print(f"✅ Phone validation working - {str(e)}")
    
    print("\n✅ Validation tests completed!")

if __name__ == "__main__":
    test_all()
    test_validation()