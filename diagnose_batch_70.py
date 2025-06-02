#!/usr/bin/env python3
"""Diagnose batch 70 processing issues"""

import sys
import os
sys.path.append('server')

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from models import Batch, Document
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_batch_70():
    """Check batch 70 status and documents"""
    
    # Create database connection
    DATABASE_URL = "postgresql://postgres:prodogs03@studio.local:5432/doc_eval"
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    try:
        # Get batch 70
        batch = session.query(Batch).filter(Batch.id == 70).first()
        if not batch:
            print("Batch 70 not found!")
            return
            
        print(f"Batch 70: {batch.batch_name}")
        print(f"Status: {batch.status}")
        print(f"Total documents: {batch.total_documents}")
        print(f"Processed documents: {batch.processed_documents}")
        print(f"Created: {batch.created_at}")
        print()
        
        # Get documents
        documents = session.query(Document).filter(Document.batch_id == 70).all()
        print(f"Found {len(documents)} documents in batch 70:")
        
        # Check for documents with specific file sizes
        target_size = 1398101 * 3 // 4  # Approximate original size
        print(f"\nLooking for documents around {target_size} bytes (~{target_size/1024/1024:.2f} MB)...")
        
        for doc in documents:
            print(f"\nDocument {doc.id}: {doc.filename}")
            print(f"  Path: {doc.filepath}")
            print(f"  Status: {doc.status}")
            print(f"  File size: {doc.file_size} bytes")
            
            # Check if file exists
            if os.path.exists(doc.filepath):
                actual_size = os.path.getsize(doc.filepath)
                print(f"  Actual file size: {actual_size} bytes")
                
                # Calculate expected base64 size
                expected_b64_size = (actual_size * 4 + 2) // 3
                print(f"  Expected base64 size: {expected_b64_size} characters")
                
                if abs(expected_b64_size - 1398101) < 100:
                    print(f"  ⚠️  POTENTIAL MATCH for 1398101 character issue!")
            else:
                print(f"  ❌ File not found!")
                
        # Check config snapshot
        if batch.config_snapshot:
            print(f"\n\nConfig snapshot available: {len(str(batch.config_snapshot))} characters")
            connections = batch.config_snapshot.get('connections', [])
            prompts = batch.config_snapshot.get('prompts', [])
            print(f"Connections: {len(connections)}")
            print(f"Prompts: {len(prompts)}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    check_batch_70()