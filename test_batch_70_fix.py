#!/usr/bin/env python3
"""Test script to verify batch 70 fix"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import Batch, Document

def test_batch_70():
    """Test batch 70 data"""
    session = Session()
    try:
        # Check if batch 70 exists
        batch = session.query(Batch).filter_by(id=70).first()
        if batch:
            print(f"Batch 70 found:")
            print(f"  ID: {batch.id}")
            print(f"  Name: {batch.batch_name}")
            print(f"  Status: {batch.status}")
            print(f"  Folder IDs: {batch.folder_ids}")
            
            # Check documents
            doc_count = session.query(Document).filter_by(batch_id=70).count()
            print(f"  Documents: {doc_count}")
            
            # Import batch service and test the method
            from services.batch_service import batch_service
            
            print("\nTesting get_batch_info method:")
            batch_info = batch_service.get_batch_info(70)
            if batch_info:
                print("Batch info retrieved successfully:")
                for key, value in batch_info.items():
                    print(f"  {key}: {value}")
            else:
                print("ERROR: get_batch_info returned None")
                
        else:
            print("Batch 70 not found in database")
            
    except Exception as e:
        print(f"Error: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    print("Testing Batch 70 Fix")
    print("=" * 50)
    test_batch_70()