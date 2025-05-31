#!/usr/bin/env python3
"""
Debug script to investigate folder status cycling issue
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import Folder, Document
from sqlalchemy import text

def debug_folder_status():
    """Debug folder status and identify the cycling issue"""
    session = Session()
    
    try:
        print("🔍 Debugging Folder Status Cycling Issue")
        print("=" * 50)
        
        # Get all folders
        folders = session.query(Folder).all()
        
        print(f"📁 Found {len(folders)} folders:")
        print()
        
        for folder in folders:
            print(f"Folder ID: {folder.id}")
            print(f"  Name: {folder.folder_name}")
            print(f"  Path: {folder.folder_path}")
            print(f"  Active: {folder.active}")
            print(f"  Status: {folder.status}")
            print(f"  Created: {folder.created_at}")
            
            # Check documents for this folder
            documents = session.query(Document).filter(Document.folder_id == folder.id).all()
            print(f"  Documents: {len(documents)} total")
            
            if documents:
                valid_docs = [d for d in documents if d.valid == 'Y']
                invalid_docs = [d for d in documents if d.valid == 'N']
                print(f"    Valid: {len(valid_docs)}")
                print(f"    Invalid: {len(invalid_docs)}")
                
                # Show first few documents
                print(f"    Sample documents:")
                for i, doc in enumerate(documents[:3]):
                    print(f"      {i+1}. {doc.filename} (valid={doc.valid})")
            
            print()
        
        # Check for potential issues
        print("🔍 Potential Issues:")
        print("-" * 30)
        
        # Issue 1: Folders with status READY but no documents
        ready_folders_no_docs = []
        for folder in folders:
            if folder.status == 'READY':
                doc_count = session.query(Document).filter(Document.folder_id == folder.id).count()
                if doc_count == 0:
                    ready_folders_no_docs.append(folder)
        
        if ready_folders_no_docs:
            print(f"❌ Found {len(ready_folders_no_docs)} folders with status READY but no documents:")
            for folder in ready_folders_no_docs:
                print(f"   - Folder {folder.id}: {folder.folder_name}")
        
        # Issue 2: Active folders that are not READY
        active_not_ready = []
        for folder in folders:
            if folder.active and folder.status != 'READY':
                active_not_ready.append(folder)
        
        if active_not_ready:
            print(f"❌ Found {len(active_not_ready)} active folders that are not READY:")
            for folder in active_not_ready:
                print(f"   - Folder {folder.id}: {folder.folder_name} (status: {folder.status})")
        
        # Issue 3: Check for missing status column values
        null_status_folders = []
        for folder in folders:
            if folder.status is None:
                null_status_folders.append(folder)
        
        if null_status_folders:
            print(f"❌ Found {len(null_status_folders)} folders with NULL status:")
            for folder in null_status_folders:
                print(f"   - Folder {folder.id}: {folder.folder_name}")
        
        # Issue 4: Check database schema
        print("\n🔍 Database Schema Check:")
        print("-" * 30)
        
        # Check if status column exists and has default value
        result = session.execute(text("""
            SELECT column_name, column_default, is_nullable, data_type
            FROM information_schema.columns 
            WHERE table_name = 'folders' AND column_name = 'status'
        """))
        
        status_column = result.fetchone()
        if status_column:
            print(f"✅ Status column exists:")
            print(f"   - Default: {status_column[1]}")
            print(f"   - Nullable: {status_column[2]}")
            print(f"   - Type: {status_column[3]}")
        else:
            print("❌ Status column does not exist!")
        
        # Check for any folders that might be getting reset
        print("\n🔍 Recent Status Changes:")
        print("-" * 30)
        
        # Look for folders that were recently created or updated
        recent_folders = session.execute(text("""
            SELECT id, folder_name, status, active, created_at
            FROM folders 
            ORDER BY created_at DESC 
            LIMIT 5
        """)).fetchall()
        
        for folder in recent_folders:
            print(f"   - ID {folder[0]}: {folder[1]} | Status: {folder[2]} | Active: {folder[3]} | Created: {folder[4]}")
        
    except Exception as e:
        print(f"❌ Error during debugging: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        session.close()

if __name__ == "__main__":
    debug_folder_status()
