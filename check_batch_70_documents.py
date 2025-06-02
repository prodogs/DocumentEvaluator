#!/usr/bin/env python3
"""Check documents in batch 70 to identify the base64 encoding issue"""

import os
import sys

# Add server directory to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import Document, Batch
import base64

def check_batch_70_documents():
    """Check documents in batch 70 and their content"""
    session = Session()
    try:
        # Get batch 70
        batch = session.query(Batch).filter_by(id=70).first()
        if not batch:
            print("Batch 70 not found!")
            return
            
        print(f"\nBatch 70: {batch.batch_name}")
        print(f"Status: {batch.status}")
        print(f"Created: {batch.created_at}")
        
        # Get documents in batch 70
        documents = session.query(Document).filter_by(batch_id=70).order_by(Document.id).all()
        
        print(f"\nFound {len(documents)} documents in batch 70:")
        print("-" * 80)
        
        for doc in documents:
            print(f"\nDocument ID: {doc.id}")
            print(f"Filename: {doc.filename}")
            print(f"Filepath: {doc.filepath}")
            print(f"File size: {doc.file_size} bytes")
            print(f"Content type: {doc.content_type}")
            print(f"Doc type: {doc.doc_type}")
            
            # Check if file exists
            if os.path.exists(doc.filepath):
                actual_size = os.path.getsize(doc.filepath)
                print(f"Actual file size: {actual_size} bytes")
                
                # Try to read and encode the file
                try:
                    with open(doc.filepath, 'rb') as f:
                        content = f.read()
                    
                    # Calculate base64 encoded size
                    encoded = base64.b64encode(content).decode('utf-8')
                    encoded_size = len(encoded)
                    print(f"Base64 encoded size: {encoded_size} characters")
                    
                    # Check if this is the problematic size
                    if encoded_size == 1398101:
                        print("⚠️  THIS IS THE PROBLEMATIC DOCUMENT!")
                        print(f"The base64 encoded content has exactly 1398101 characters")
                        print(f"This number mod 4 = {1398101 % 4}")
                        
                        # Check file content details
                        print(f"\nFile details:")
                        print(f"First 100 bytes (hex): {content[:100].hex()}")
                        print(f"Last 100 bytes (hex): {content[-100:].hex()}")
                        
                except Exception as e:
                    print(f"Error reading/encoding file: {e}")
            else:
                print(f"⚠️  File does not exist at: {doc.filepath}")
                
        print("\n" + "-" * 80)
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

if __name__ == "__main__":
    check_batch_70_documents()