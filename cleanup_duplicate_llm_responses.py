#!/usr/bin/env python3
"""
Clean up duplicate llm_responses in KnowledgeDocuments database
"""

import psycopg2
import sys

def cleanup_duplicates():
    """Remove duplicate llm_responses keeping only the first one for each unique combination"""
    try:
        conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        cursor = conn.cursor()
        
        # First, show current state
        cursor.execute("""
            SELECT batch_id, COUNT(*) as total, 
                   COUNT(DISTINCT (document_id, prompt_id, connection_id)) as unique_combos
            FROM llm_responses 
            GROUP BY batch_id
            HAVING COUNT(*) > COUNT(DISTINCT (document_id, prompt_id, connection_id))
        """)
        
        print("Batches with duplicate llm_responses:")
        duplicates_found = False
        for row in cursor.fetchall():
            duplicates_found = True
            batch_id, total, unique_combos = row
            print(f"  Batch {batch_id}: {total} total, {unique_combos} unique (duplicates: {total - unique_combos})")
        
        if not duplicates_found:
            print("No duplicates found!")
            return
        
        # Delete duplicates, keeping the one with lowest ID for each combination
        cursor.execute("""
            DELETE FROM llm_responses a
            WHERE EXISTS (
                SELECT 1
                FROM llm_responses b
                WHERE a.document_id = b.document_id
                  AND a.prompt_id = b.prompt_id
                  AND a.connection_id = b.connection_id
                  AND a.batch_id = b.batch_id
                  AND a.id > b.id
            )
        """)
        
        deleted_count = cursor.rowcount
        print(f"\nDeleted {deleted_count} duplicate records")
        
        # Also reset any stuck PROCESSING statuses to QUEUED
        cursor.execute("""
            UPDATE llm_responses 
            SET status = 'QUEUED',
                started_processing_at = NULL,
                task_id = NULL
            WHERE status = 'PROCESSING'
        """)
        
        reset_count = cursor.rowcount
        if reset_count > 0:
            print(f"Reset {reset_count} stuck PROCESSING records to QUEUED")
        
        # Show final state
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM llm_responses 
            GROUP BY status 
            ORDER BY COUNT(*) DESC
        """)
        
        print("\nFinal llm_responses by status:")
        for row in cursor.fetchall():
            print(f"  {row[0]}: {row[1]}")
        
        # Commit changes
        conn.commit()
        print("\nCleanup completed successfully!")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Cleaning up duplicate llm_responses...")
    cleanup_duplicates()