#!/usr/bin/env python3
"""
Check batch 79 entries in llm_responses table and any QUEUED items
in the KnowledgeDocuments database
"""

import psycopg2
import json
from datetime import datetime

def check_knowledge_documents_db():
    """Check the KnowledgeDocuments database for batch 79 and QUEUED items"""
    
    try:
        # Connect to KnowledgeDocuments database
        conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        cursor = conn.cursor()
        
        print("Connected to KnowledgeDocuments database successfully!")
        print("=" * 80)
        
        # Check for batch 79 entries
        print("\n1. CHECKING BATCH 79 ENTRIES IN llm_responses:")
        print("-" * 60)
        
        cursor.execute("""
            SELECT id, document_id, batch_id, status, 
                   created_at, started_processing_at, completed_processing_at,
                   error_message, task_id
            FROM llm_responses 
            WHERE batch_id = 79
            ORDER BY created_at DESC
        """)
        
        batch_79_entries = cursor.fetchall()
        
        if batch_79_entries:
            print(f"Found {len(batch_79_entries)} entries for batch 79:")
            print()
            
            # Group by status
            status_counts = {}
            for entry in batch_79_entries:
                status = entry[3]
                status_counts[status] = status_counts.get(status, 0) + 1
            
            print("Status breakdown:")
            for status, count in sorted(status_counts.items()):
                print(f"  {status}: {count}")
            
            print("\nDetailed entries (first 10):")
            for i, entry in enumerate(batch_79_entries[:10]):
                print(f"\n  Entry {i+1}:")
                print(f"    ID: {entry[0]}")
                print(f"    Document ID: {entry[1]}")
                print(f"    Status: {entry[3]}")
                print(f"    Created: {entry[4]}")
                print(f"    Started Processing: {entry[5]}")
                print(f"    Completed: {entry[6]}")
                if entry[7]:  # error_message
                    print(f"    Error: {entry[7][:100]}...")
                if entry[8]:  # task_id
                    print(f"    Task ID: {entry[8]}")
        else:
            print("No entries found for batch 79 in llm_responses table")
        
        # Check for ANY QUEUED items
        print("\n\n2. CHECKING FOR ANY QUEUED ITEMS:")
        print("-" * 60)
        
        cursor.execute("""
            SELECT batch_id, COUNT(*) as count
            FROM llm_responses 
            WHERE status = 'QUEUED'
            GROUP BY batch_id
            ORDER BY batch_id
        """)
        
        queued_batches = cursor.fetchall()
        
        if queued_batches:
            print(f"Found QUEUED items in {len(queued_batches)} batch(es):")
            total_queued = 0
            for batch_id, count in queued_batches:
                print(f"  Batch {batch_id}: {count} QUEUED items")
                total_queued += count
            print(f"\nTotal QUEUED items: {total_queued}")
            
            # Show sample of QUEUED items
            print("\nSample of QUEUED items (first 5):")
            cursor.execute("""
                SELECT id, document_id, batch_id, created_at, prompt_id, connection_id
                FROM llm_responses 
                WHERE status = 'QUEUED'
                ORDER BY created_at ASC
                LIMIT 5
            """)
            
            queued_samples = cursor.fetchall()
            for i, sample in enumerate(queued_samples):
                print(f"\n  QUEUED Item {i+1}:")
                print(f"    ID: {sample[0]}")
                print(f"    Document ID: {sample[1]}")
                print(f"    Batch ID: {sample[2]}")
                print(f"    Created: {sample[3]}")
                print(f"    Prompt ID: {sample[4]}")
                print(f"    Connection ID: {sample[5]}")
        else:
            print("No QUEUED items found in llm_responses table")
        
        # Check overall status distribution
        print("\n\n3. OVERALL STATUS DISTRIBUTION IN llm_responses:")
        print("-" * 60)
        
        cursor.execute("""
            SELECT status, COUNT(*) as count
            FROM llm_responses 
            GROUP BY status
            ORDER BY count DESC
        """)
        
        status_distribution = cursor.fetchall()
        
        print("Status distribution across all batches:")
        total_items = 0
        for status, count in status_distribution:
            print(f"  {status}: {count:,}")
            total_items += count
        print(f"\nTotal items in llm_responses: {total_items:,}")
        
        # Check for recent activity
        print("\n\n4. RECENT ACTIVITY:")
        print("-" * 60)
        
        cursor.execute("""
            SELECT MAX(created_at) as last_created,
                   MAX(started_processing_at) as last_started,
                   MAX(completed_processing_at) as last_completed
            FROM llm_responses
        """)
        
        recent_activity = cursor.fetchone()
        print(f"Last item created: {recent_activity[0]}")
        print(f"Last processing started: {recent_activity[1]}")
        print(f"Last processing completed: {recent_activity[2]}")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error connecting to KnowledgeDocuments database: {e}")
        print("\nPlease ensure:")
        print("1. The KnowledgeDocuments database exists on studio.local")
        print("2. PostgreSQL is running on port 5432")
        print("3. The credentials are correct")

if __name__ == "__main__":
    check_knowledge_documents_db()