#!/usr/bin/env python3
"""
Test the Document Type API endpoints
"""

import requests
import json

def test_document_type_api():
    """Test document type API endpoints"""
    
    base_url = "http://192.168.1.138:5001"  # Adjust as needed
    
    print("Testing Document Type API")
    print("=" * 50)
    
    # Test 1: Get all document types
    print("\n1. Testing GET /api/document-types")
    try:
        response = requests.get(f"{base_url}/api/document-types")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Found {data['total']} document types")
            print(f"Sample types: {[dt['file_extension'] for dt in data['document_types'][:5]]}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 2: Get valid document types only
    print("\n2. Testing GET /api/document-types/valid")
    try:
        response = requests.get(f"{base_url}/api/document-types/valid")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: Found {data['total']} valid extensions")
            print(f"Valid extensions: {data['valid_extensions'][:10]}...")
            print(f"Supported description: {data['supported_description'][:100]}...")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 3: Validate file list
    print("\n3. Testing POST /api/document-types/validate")
    try:
        test_files = [
            "document.pdf",
            "spreadsheet.xlsx", 
            "image.jpg",
            "source.py",
            "archive.zip"
        ]
        
        response = requests.post(
            f"{base_url}/api/document-types/validate",
            json={"filenames": test_files},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data['summary']}")
            print(f"Valid files: {data['valid_files']}")
            print(f"Invalid files: {data['invalid_files']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 4: Get info for specific extension
    print("\n4. Testing GET /api/document-types/pdf")
    try:
        response = requests.get(f"{base_url}/api/document-types/pdf")
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: PDF info - {data['file_type_info']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 5: Add a new document type
    print("\n5. Testing POST /api/document-types (add new type)")
    try:
        new_type = {
            "extension": ".test",
            "mime_type": "application/test",
            "description": "Test file type",
            "is_valid": True,
            "supports_text_extraction": True
        }
        
        response = requests.post(
            f"{base_url}/api/document-types",
            json=new_type,
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data['message']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    # Test 6: Update document type validity
    print("\n6. Testing PUT /api/document-types/test/validity")
    try:
        response = requests.put(
            f"{base_url}/api/document-types/test/validity",
            json={"is_valid": False},
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Success: {data['message']}")
        else:
            print(f"❌ Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"❌ Error: {e}")
    
    print("\n" + "=" * 50)
    print("API testing completed!")

if __name__ == "__main__":
    test_document_type_api()