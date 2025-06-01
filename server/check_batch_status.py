#!/usr/bin/env python3
"""
Quick check of batch status to identify the issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Session
from models import Batch, LlmResponse, Document

def quick_check():
    """Quick check of all batches"""
    
    session = Session()
    
    try:
        print("📊 QUICK BATCH STATUS CHECK")
        print("=" * 40)
        
        # Get all batches
        batches = session.query(Batch).order_by(Batch.id.desc()).all()
        
        if not batches:
            print("No batches found")
            return
        
        print(f"Total batches: {len(batches)}")
        print()
        
        for batch in batches:
            # Count documents and responses
            doc_count = session.query(Document).filter(Document.batch_id == batch.id).count()
            response_count = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch.id
            ).count()
            
            status_icon = "✅" if response_count > 0 else "❌" if batch.status == 'COMPLETED' else "⏳"
            
            print(f"{status_icon} Batch #{batch.batch_number} - {batch.batch_name}")
            print(f"   Status: {batch.status}")
            print(f"   Documents: {doc_count}, Responses: {response_count}")
            
            if batch.status == 'COMPLETED' and response_count == 0:
                print(f"   🚨 ISSUE: Marked completed but no responses!")
            
            print()
        
    finally:
        session.close()

if __name__ == "__main__":
    quick_check()
