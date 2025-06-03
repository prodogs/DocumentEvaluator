#!/usr/bin/env python3
"""
Fix stuck batch 2 that's in PROCESSING status with orphaned tasks
"""

import sys
sys.path.insert(0, 'server')
from database import Session, get_engine
from models import Batch
import psycopg2
from datetime import datetime

def fix_stuck_batch():
    print("Fixing stuck batch 2...")
    
    # Update batch status in doc_eval database
    session = Session()
    try:
        batch = session.query(Batch).filter_by(id=2).first()
        if batch:
            print(f"Current batch status: {batch.status}")
            
            # Reset to COMPLETED since 6 out of 8 documents are done
            batch.status = 'COMPLETED'
            batch.completed_at = datetime.now()
            session.commit()
            print(f"Updated batch status to COMPLETED")
        else:
            print("Batch 2 not found!")
    finally:
        session.close()
    
    # Update stuck LLM responses in KnowledgeDocuments database
    try:
        kb_conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        kb_cursor = kb_conn.cursor()
        
        # Mark stuck PROCESSING tasks as FAILED
        kb_cursor.execute("""
            UPDATE llm_responses
            SET status = 'FAILED',
                error_message = 'Marked as failed due to stuck processing state',
                completed_processing_at = NOW()
            WHERE batch_id = 2 
            AND status = 'PROCESSING'
            RETURNING id, task_id
        """)
        
        updated_rows = kb_cursor.fetchall()
        print(f"Updated {len(updated_rows)} stuck LLM responses to FAILED status")
        for row in updated_rows:
            print(f"  - Response ID {row[0]}, Task ID: {row[1]}")
        
        kb_conn.commit()
        kb_cursor.close()
        kb_conn.close()
        
    except Exception as e:
        print(f"Error updating KnowledgeDocuments: {e}")
    
    print("Done! Batch 2 should now be in COMPLETED status.")

if __name__ == "__main__":
    fix_stuck_batch()