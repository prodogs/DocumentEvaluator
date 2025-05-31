#!/usr/bin/env python3
"""
Test script to debug the folder status API issue
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import Folder, Document, Doc
from sqlalchemy import func, case
from services.folder_preprocessing_service import FolderPreprocessingService

def test_folder_status_query():
    """Test the folder status query directly"""
    session = Session()
    
    try:
        print("🔍 Testing Folder Status Query")
        print("=" * 50)
        
        # First, check if folder exists
        folder = session.query(Folder).filter(Folder.id == 1).first()
        if folder:
            print(f"✅ Folder 1 exists:")
            print(f"   Name: {folder.folder_name}")
            print(f"   Path: {folder.folder_path}")
            print(f"   Status: {folder.status}")
            print(f"   Active: {folder.active}")
        else:
            print("❌ Folder 1 does not exist")
            return
        
        print()
        
        # Test the exact query from get_folder_status
        print("🔍 Testing the exact query from get_folder_status:")
        
        result = session.query(
            Folder.id,
            Folder.folder_name,
            Folder.folder_path,
            Folder.status,
            func.count(Document.id).label('total_documents'),
            func.sum(case((Document.valid == 'Y', 1), else_=0)).label('valid_documents'),
            func.sum(case((Document.valid == 'N', 1), else_=0)).label('invalid_documents'),
            func.coalesce(func.sum(Doc.file_size), 0).label('total_size')
        ).outerjoin(Document, Folder.id == Document.folder_id)\
         .outerjoin(Doc, Document.id == Doc.document_id)\
         .filter(Folder.id == 1)\
         .group_by(Folder.id, Folder.folder_name, Folder.folder_path, Folder.status)\
         .first()
        
        if result:
            print("✅ Query returned result:")
            print(f"   Folder ID: {result[0]}")
            print(f"   Folder Name: {result[1]}")
            print(f"   Folder Path: {result[2]}")
            print(f"   Status: {result[3]}")
            print(f"   Total Documents: {result[4]}")
            print(f"   Valid Documents: {result[5]}")
            print(f"   Invalid Documents: {result[6]}")
            print(f"   Total Size: {result[7]}")
        else:
            print("❌ Query returned None")
        
        print()
        
        # Test using the service
        print("🔍 Testing FolderPreprocessingService.get_folder_status:")
        service = FolderPreprocessingService()
        status = service.get_folder_status(1)
        
        if status:
            print("✅ Service returned status:")
            for key, value in status.items():
                print(f"   {key}: {value}")
        else:
            print("❌ Service returned None")
        
        print()
        
        # Check documents table directly
        print("🔍 Checking documents table for folder 1:")
        documents = session.query(Document).filter(Document.folder_id == 1).all()
        print(f"   Found {len(documents)} documents")
        
        for doc in documents:
            print(f"   - {doc.filename}: valid={doc.valid}")
        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()

if __name__ == "__main__":
    test_folder_status_query()
