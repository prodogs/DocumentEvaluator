#!/usr/bin/env python3
"""
Fix stuck processing items by resetting them to QUEUED status
"""

import psycopg2
from datetime import datetime, timedelta
import sys

def fix_stuck_items(older_than_minutes=30):
    """Reset stuck PROCESSING items back to QUEUED"""
    try:
        conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        cursor = conn.cursor()
        
        # Find stuck items
        threshold = datetime.now() - timedelta(minutes=older_than_minutes)
        cursor.execute("""
            SELECT COUNT(*) 
            FROM llm_responses 
            WHERE status = 'PROCESSING' 
            AND started_processing_at < %s
        """, (threshold,))
        
        stuck_count = cursor.fetchone()[0]
        
        if stuck_count == 0:
            print(f"No items stuck for more than {older_than_minutes} minutes")
            return True
        
        print(f"Found {stuck_count} items stuck in PROCESSING for more than {older_than_minutes} minutes")
        
        # Reset them to QUEUED
        cursor.execute("""
            UPDATE llm_responses 
            SET status = 'QUEUED',
                started_processing_at = NULL,
                task_id = NULL,
                updated_at = NOW()
            WHERE status = 'PROCESSING' 
            AND started_processing_at < %s
            RETURNING id, batch_id
        """, (threshold,))
        
        reset_items = cursor.fetchall()
        
        print(f"\nReset {len(reset_items)} items to QUEUED status:")
        batch_counts = {}
        for id, batch_id in reset_items:
            batch_counts[batch_id] = batch_counts.get(batch_id, 0) + 1
        
        for batch_id, count in batch_counts.items():
            print(f"  Batch {batch_id}: {count} items")
        
        # Also mark any FAILED batches as READY if they have QUEUED items
        cursor.execute("""
            UPDATE llm_responses
            SET status = 'READY_TO_RETRY'
            WHERE status = 'FAILED'
            AND batch_id IN (
                SELECT DISTINCT batch_id 
                FROM llm_responses 
                WHERE status = 'QUEUED'
            )
        """)
        
        # Commit changes
        conn.commit()
        
        # Show final status
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM llm_responses 
            GROUP BY status
            ORDER BY status
        """)
        
        print("\nFinal status distribution:")
        for status, count in cursor.fetchall():
            print(f"  {status}: {count}")
        
        cursor.close()
        conn.close()
        
        return True
        
    except Exception as e:
        print(f"Error: {e}")
        return False

if __name__ == "__main__":
    print("Fixing stuck processing items...")
    
    # Check for custom threshold
    threshold = 30
    if len(sys.argv) > 1:
        try:
            threshold = int(sys.argv[1])
        except:
            print(f"Usage: {sys.argv[0]} [minutes_threshold]")
            print(f"Using default threshold of {threshold} minutes")
    
    success = fix_stuck_items(threshold)
    sys.exit(0 if success else 1)