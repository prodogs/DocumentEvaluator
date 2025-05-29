#!/usr/bin/env python3
"""
Test script for folder preprocessing functionality
"""

import sys
import os
import tempfile
import json

# Add server directory to path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from server.services.folder_preprocessing_service import FolderPreprocessingService

def create_test_folder():
    """Create a temporary folder with test files"""
    temp_dir = tempfile.mkdtemp(prefix="test_folder_")
    
    # Create some test files
    test_files = [
        ("document1.pdf", b"PDF content here"),
        ("document2.txt", b"This is a text document"),
        ("spreadsheet.xlsx", b"Excel content"),
        ("invalid.xyz", b"Unknown file type"),
        ("empty.txt", b""),  # Empty file
        ("large.txt", b"x" * 1000),  # Normal size file
    ]
    
    for filename, content in test_files:
        file_path = os.path.join(temp_dir, filename)
        with open(file_path, 'wb') as f:
            f.write(content)
    
    print(f"Created test folder: {temp_dir}")
    return temp_dir

def test_folder_preprocessing():
    """Test the folder preprocessing service"""
    
    # Create test folder
    test_folder = create_test_folder()
    
    try:
        # Initialize preprocessing service
        service = FolderPreprocessingService()
        
        # Test preprocessing
        print(f"\n🔄 Testing folder preprocessing...")
        results = service.preprocess_folder(test_folder, "Test Folder")
        
        print(f"\n📊 Preprocessing Results:")
        print(f"  Folder ID: {results['folder_id']}")
        print(f"  Folder Name: {results['folder_name']}")
        print(f"  Total Files: {results['total_files']}")
        print(f"  Valid Files: {results['valid_files']}")
        print(f"  Invalid Files: {results['invalid_files']}")
        print(f"  Total Size: {results['total_size']} bytes")
        
        if results['errors']:
            print(f"  Errors: {len(results['errors'])}")
            for error in results['errors']:
                print(f"    - {error}")
        
        # Test getting folder status
        print(f"\n📋 Testing folder status retrieval...")
        status = service.get_folder_status(results['folder_id'])
        
        if status:
            print(f"  Status: {status['status']}")
            print(f"  Total Documents: {status['total_documents']}")
            print(f"  Valid Documents: {status['valid_documents']}")
            print(f"  Invalid Documents: {status['invalid_documents']}")
            print(f"  Total Size: {status['total_size']} bytes")
        else:
            print("  ❌ Could not retrieve folder status")
        
        print(f"\n✅ Folder preprocessing test completed successfully!")
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up test folder
        import shutil
        shutil.rmtree(test_folder)
        print(f"\n🧹 Cleaned up test folder: {test_folder}")

if __name__ == "__main__":
    print("🧪 Testing Folder Preprocessing Service")
    print("=" * 50)
    test_folder_preprocessing()
