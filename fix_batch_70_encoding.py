#!/usr/bin/env python3
"""Fix batch 70 encoding issue by cleaning up and retrying"""

import os
import sys
import psycopg2
import base64

# Add server directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import Batch

def fix_batch_70():
    """Clean up any existing batch 70 docs in KnowledgeDocuments and reset batch"""
    
    print("=== Fixing Batch 70 Base64 Encoding Issue ===\n")
    
    # Step 1: Clean up KnowledgeDocuments database
    print("Step 1: Cleaning up KnowledgeDocuments database...")
    try:
        kb_conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        kb_cursor = kb_conn.cursor()
        
        # Check for existing batch 70 documents
        kb_cursor.execute("""
            SELECT id, document_id, LENGTH(content) as content_length, file_size
            FROM docs
            WHERE document_id LIKE 'batch_70_%'
        """)
        
        existing_docs = kb_cursor.fetchall()
        if existing_docs:
            print(f"Found {len(existing_docs)} existing documents for batch 70:")
            for doc in existing_docs:
                print(f"  ID: {doc[0]}, DocID: {doc[1]}, Content Length: {doc[2]}, File Size: {doc[3]}")
                if doc[2] == 1398101:
                    print(f"    ⚠️ PROBLEMATIC DOCUMENT!")
            
            # Delete them
            kb_cursor.execute("DELETE FROM docs WHERE document_id LIKE 'batch_70_%'")
            deleted_count = kb_cursor.rowcount
            kb_conn.commit()
            print(f"✅ Deleted {deleted_count} documents from KnowledgeDocuments")
        else:
            print("✅ No existing batch 70 documents found in KnowledgeDocuments")
        
        kb_cursor.close()
        kb_conn.close()
        
    except Exception as e:
        print(f"❌ Error cleaning KnowledgeDocuments: {e}")
        return False
    
    # Step 2: Reset batch 70 to SAVED status
    print("\nStep 2: Resetting batch 70 to SAVED status...")
    session = Session()
    try:
        batch = session.query(Batch).filter_by(id=70).first()
        if not batch:
            print("❌ Batch 70 not found!")
            return False
        
        print(f"Current batch status: {batch.status}")
        
        # Reset batch
        batch.status = 'SAVED'
        batch.started_at = None
        batch.completed_at = None
        batch.processed_documents = 0
        
        session.commit()
        print("✅ Batch 70 reset to SAVED status")
        
    except Exception as e:
        print(f"❌ Error resetting batch: {e}")
        session.rollback()
        return False
    finally:
        session.close()
    
    print("\n=== Fix Complete ===")
    print("You can now restage and run batch 70 again.")
    print("The base64 encoding fix has been applied to batch_service.py")
    
    return True

if __name__ == "__main__":
    success = fix_batch_70()
    sys.exit(0 if success else 1)