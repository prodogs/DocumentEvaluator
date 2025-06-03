#!/usr/bin/env python3
"""
Test script for document type service
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from services.document_type_service import document_type_service

def test_document_type_service():
    """Test the document type service functionality"""
    
    print("Testing Document Type Service")
    print("=" * 50)
    
    # Test 1: Get valid extensions
    print("\n1. Testing get_valid_extensions():")
    valid_extensions = document_type_service.get_valid_extensions()
    print(f"Found {len(valid_extensions)} valid extensions:")
    print(", ".join(sorted(valid_extensions)[:10]) + "..." if len(valid_extensions) > 10 else ", ".join(sorted(valid_extensions)))
    
    # Test 2: Test file validation
    print("\n2. Testing file validation:")
    test_files = [
        "document.pdf",
        "spreadsheet.xlsx", 
        "presentation.pptx",
        "source.py",
        "data.json",
        "image.jpg",
        "archive.zip",
        "executable.exe",
        "text.txt",
        "unknown.xyz"
    ]
    
    for filename in test_files:
        is_valid = document_type_service.is_valid_file_type(filename)
        info = document_type_service.get_file_type_info(filename)
        status = "✅ VALID" if is_valid else "❌ INVALID"
        print(f"{filename:<15} {status:<10} {info['description']}")
    
    # Test 3: Test batch validation
    print("\n3. Testing batch validation:")
    valid_files, invalid_files = document_type_service.validate_file_batch(test_files)
    print(f"Valid files ({len(valid_files)}): {', '.join(valid_files)}")
    print(f"Invalid files ({len(invalid_files)}): {', '.join(invalid_files)}")
    
    # Test 4: Get supported extensions list
    print("\n4. Supported extensions description:")
    supported_desc = document_type_service.get_supported_extensions_list()
    print(supported_desc)
    
    # Test 5: Test MIME type mapping
    print("\n5. MIME type mapping (first 10):")
    mime_types = document_type_service.get_mime_type_mapping()
    for i, (ext, mime) in enumerate(sorted(mime_types.items())[:10]):
        print(f"{ext:<8} -> {mime}")
    
    print(f"\nTotal MIME types configured: {len(mime_types)}")
    
    print("\n" + "=" * 50)
    print("✅ Document Type Service test completed successfully!")

if __name__ == "__main__":
    test_document_type_service()