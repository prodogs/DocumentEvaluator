#!/usr/bin/env python3
"""
Test script to verify that .md (markdown) files are properly supported
across all components of the document evaluation system.
"""

import os
import tempfile
import sys
from pathlib import Path

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from services.folder_preprocessing_service import FolderPreprocessingService
from services.document_encoding_service import DocumentEncodingService
from api.process_folder import traverse_directory

def create_test_markdown_file():
    """Create a temporary markdown file for testing"""
    content = """# Test Markdown Document

This is a test markdown document to verify that .md files are properly supported.

## Features

- **Bold text**
- *Italic text*
- `Code snippets`

## Code Block

```python
def hello_world():
    print("Hello, World!")
```

## Table

| Column 1 | Column 2 | Column 3 |
|----------|----------|----------|
| Value 1  | Value 2  | Value 3  |

## Conclusion

This markdown file should be recognized and processed by the document evaluation system.
"""
    
    # Create temporary file
    temp_file = tempfile.NamedTemporaryFile(mode='w', suffix='.md', delete=False)
    temp_file.write(content)
    temp_file.close()
    
    return temp_file.name

def test_folder_preprocessing_service():
    """Test that FolderPreprocessingService supports .md files"""
    print("🧪 Testing FolderPreprocessingService...")
    
    service = FolderPreprocessingService()
    
    # Check if .md is in VALID_EXTENSIONS
    if '.md' in service.VALID_EXTENSIONS:
        print("   ✅ .md extension found in VALID_EXTENSIONS")
        return True
    else:
        print("   ❌ .md extension NOT found in VALID_EXTENSIONS")
        return False

def test_document_encoding_service():
    """Test that DocumentEncodingService supports .md files"""
    print("🧪 Testing DocumentEncodingService...")
    
    service = DocumentEncodingService()
    
    # Check if .md is in supported_extensions
    if '.md' in service.supported_extensions:
        print("   ✅ .md extension found in supported_extensions")
        return True
    else:
        print("   ❌ .md extension NOT found in supported_extensions")
        return False

def test_service_client_mime_type():
    """Test that RAGServiceClient properly handles .md MIME type"""
    print("🧪 Testing RAGServiceClient MIME type handling...")

    from services.client import RAGServiceClient
    client = RAGServiceClient()

    # Test MIME type detection for .md files
    mime_type = client._get_mime_type("test_document.md")

    if mime_type == "text/markdown":
        print("   ✅ .md files correctly mapped to text/markdown MIME type")
        return True
    else:
        print(f"   ❌ .md files mapped to incorrect MIME type: {mime_type}")
        return False

def test_traverse_directory():
    """Test that traverse_directory function includes .md files"""
    print("🧪 Testing traverse_directory function...")
    
    # Create a temporary directory with a markdown file
    temp_dir = tempfile.mkdtemp()
    md_file = create_test_markdown_file()
    
    # Move the markdown file to the temp directory
    md_filename = os.path.basename(md_file)
    new_md_path = os.path.join(temp_dir, md_filename)
    os.rename(md_file, new_md_path)
    
    try:
        # Test traverse_directory
        files = traverse_directory(temp_dir)
        
        # Check if our markdown file was found
        md_files = [f for f in files if f.endswith('.md')]
        
        if md_files:
            print(f"   ✅ Found {len(md_files)} .md file(s) in directory scan")
            print(f"      File: {os.path.basename(md_files[0])}")
            return True
        else:
            print("   ❌ No .md files found in directory scan")
            return False
    
    finally:
        # Cleanup
        if os.path.exists(new_md_path):
            os.remove(new_md_path)
        os.rmdir(temp_dir)

def test_file_validation():
    """Test file validation with a real markdown file"""
    print("🧪 Testing file validation with real .md file...")
    
    # Create a test markdown file
    md_file = create_test_markdown_file()
    
    try:
        service = FolderPreprocessingService()
        
        # Get file info
        file_info = {
            'path': md_file,
            'name': os.path.basename(md_file),
            'extension': '.md',
            'size': os.path.getsize(md_file),
            'relative_path': os.path.basename(md_file)
        }
        
        # Validate the file
        is_valid, reason = service._validate_file(file_info)
        
        if is_valid:
            print(f"   ✅ Markdown file validation passed: {reason}")
            return True
        else:
            print(f"   ❌ Markdown file validation failed: {reason}")
            return False
    
    finally:
        # Cleanup
        if os.path.exists(md_file):
            os.remove(md_file)

def main():
    """Run all markdown support tests"""
    print("🚀 Testing Markdown (.md) File Support")
    print("=" * 50)
    
    tests = [
        ("FolderPreprocessingService", test_folder_preprocessing_service),
        ("DocumentEncodingService", test_document_encoding_service),
        ("RAGServiceClient MIME Type", test_service_client_mime_type),
        ("traverse_directory", test_traverse_directory),
        ("File Validation", test_file_validation)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"   ❌ Test failed with exception: {e}")
            results.append((test_name, False))
        print()
    
    # Summary
    print("=" * 50)
    print("📋 Test Results Summary:")
    print("=" * 50)
    
    passed = 0
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
        if result:
            passed += 1
    
    print("=" * 50)
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All tests passed! Markdown (.md) files are fully supported.")
        return True
    else:
        print("⚠️  Some tests failed. Markdown support may be incomplete.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
