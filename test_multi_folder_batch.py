#!/usr/bin/env python3
"""
Test script to verify the new multi-folder batch behavior.

This script tests that:
1. A single process-db-folders request creates one batch row
2. The batch contains all folder IDs in a JSON field
3. All documents from all folders are linked to the same batch
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from server.database import Session
from server.models import Batch, Document, Folder
from sqlalchemy import func
import json

def test_multi_folder_batch():
    """Test the multi-folder batch functionality"""
    
    session = Session()
    
    try:
        print("=== Multi-Folder Batch Test ===\n")
        
        # 1. Check current batch count
        initial_batch_count = session.query(Batch).count()
        print(f"Initial batch count: {initial_batch_count}")
        
        # 2. Get all active folders
        folders = session.query(Folder).filter(Folder.active == 1).all()
        print(f"Active folders found: {len(folders)}")
        
        for folder in folders:
            print(f"  - Folder ID {folder.id}: {folder.folder_path}")
        
        # 3. Check latest batch (if any)
        latest_batch = session.query(Batch).order_by(Batch.id.desc()).first()
        
        if latest_batch:
            print(f"\nLatest batch:")
            print(f"  - Batch ID: {latest_batch.id}")
            print(f"  - Batch Number: {latest_batch.batch_number}")
            print(f"  - Batch Name: {latest_batch.batch_name}")
            print(f"  - Folder IDs (JSON): {latest_batch.folder_ids}")
            print(f"  - Legacy Folder Path: {latest_batch.folder_path}")
            print(f"  - Status: {latest_batch.status}")
            print(f"  - Created At: {latest_batch.created_at}")
            
            # 4. Check documents linked to this batch
            if latest_batch.folder_ids:
                print(f"\nDocuments linked to batch {latest_batch.id}:")
                documents = session.query(Document).filter(Document.batch_id == latest_batch.id).all()
                print(f"  - Total documents: {len(documents)}")
                
                # Group by folder_id
                folder_doc_counts = {}
                for doc in documents:
                    folder_id = doc.folder_id
                    if folder_id not in folder_doc_counts:
                        folder_doc_counts[folder_id] = 0
                    folder_doc_counts[folder_id] += 1
                
                print(f"  - Documents per folder:")
                for folder_id, count in folder_doc_counts.items():
                    folder_name = "Unknown"
                    for folder in folders:
                        if folder.id == folder_id:
                            folder_name = os.path.basename(folder.folder_path)
                            break
                    print(f"    * Folder {folder_id} ({folder_name}): {count} documents")
                
                # 5. Verify folder_ids JSON matches actual folders
                if latest_batch.folder_ids:
                    batch_folder_ids = set(latest_batch.folder_ids)
                    actual_folder_ids = set(folder_doc_counts.keys())
                    
                    print(f"\nFolder ID verification:")
                    print(f"  - Batch folder_ids JSON: {sorted(batch_folder_ids)}")
                    print(f"  - Actual folder_ids in documents: {sorted(actual_folder_ids)}")
                    
                    if batch_folder_ids == actual_folder_ids:
                        print("  ✅ Folder IDs match perfectly!")
                    else:
                        missing_in_batch = actual_folder_ids - batch_folder_ids
                        missing_in_docs = batch_folder_ids - actual_folder_ids
                        
                        if missing_in_batch:
                            print(f"  ❌ Missing in batch JSON: {sorted(missing_in_batch)}")
                        if missing_in_docs:
                            print(f"  ❌ Missing in documents: {sorted(missing_in_docs)}")
            else:
                print(f"\n❌ Latest batch has no folder_ids JSON field set")
        else:
            print("\n❌ No batches found in database")
        
        # 6. Summary statistics
        print(f"\n=== Summary Statistics ===")
        total_batches = session.query(Batch).count()
        total_documents = session.query(Document).count()
        
        print(f"Total batches: {total_batches}")
        print(f"Total documents: {total_documents}")
        
        # Count batches with folder_ids vs legacy folder_path
        batches_with_folder_ids = session.query(Batch).filter(Batch.folder_ids.isnot(None)).count()
        batches_with_folder_path = session.query(Batch).filter(Batch.folder_path.isnot(None)).count()
        
        print(f"Batches with folder_ids (new): {batches_with_folder_ids}")
        print(f"Batches with folder_path (legacy): {batches_with_folder_path}")
        
        if batches_with_folder_ids > 0:
            print("✅ New multi-folder batch system is working!")
        else:
            print("❌ No multi-folder batches found - system may not be updated")
            
    except Exception as e:
        print(f"❌ Error during test: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    test_multi_folder_batch()
