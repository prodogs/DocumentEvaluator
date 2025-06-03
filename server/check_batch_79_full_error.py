#!/usr/bin/env python3
"""
Check the full error message for batch 79 entry in llm_responses table
"""

import psycopg2
import json

def check_batch_79_full_error():
    """Check the full error details for batch 79"""
    
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
        
        # Get full details for batch 79
        cursor.execute("""
            SELECT id, document_id, batch_id, status, 
                   error_message, connection_details, prompt_id, connection_id,
                   created_at, started_processing_at, completed_processing_at
            FROM llm_responses 
            WHERE batch_id = 79
        """)
        
        result = cursor.fetchone()
        
        if result:
            print("\nBATCH 79 FULL DETAILS:")
            print("-" * 60)
            print(f"ID: {result[0]}")
            print(f"Document ID: {result[1]}")
            print(f"Batch ID: {result[2]}")
            print(f"Status: {result[3]}")
            print(f"\nFull Error Message:")
            print("-" * 40)
            print(result[4])
            print("-" * 40)
            
            print(f"\nConnection ID: {result[7]}")
            print(f"Prompt ID: {result[6]}")
            
            if result[5]:  # connection_details
                print(f"\nConnection Details (JSON):")
                try:
                    conn_details = json.loads(result[5]) if isinstance(result[5], str) else result[5]
                    print(json.dumps(conn_details, indent=2))
                except:
                    print(result[5])
            
            print(f"\nTimestamps:")
            print(f"  Created: {result[8]}")
            print(f"  Started: {result[9]}")
            print(f"  Completed: {result[10]}")
            
            # Also check if there are more entries for this batch in the main database
            print("\n\nChecking main database (doc_eval) for batch 79 info...")
            print("-" * 60)
            
            # Connect to main database
            main_conn = psycopg2.connect(
                host="studio.local",
                database="doc_eval",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            main_cursor = main_conn.cursor()
            
            # Check batch details
            main_cursor.execute("""
                SELECT id, batch_number, batch_name, status, 
                       total_documents, processed_documents,
                       config_snapshot
                FROM batches 
                WHERE id = 79
            """)
            
            batch_info = main_cursor.fetchone()
            if batch_info:
                print(f"Batch Number: {batch_info[1]}")
                print(f"Batch Name: {batch_info[2]}")
                print(f"Batch Status: {batch_info[3]}")
                print(f"Total Documents: {batch_info[4]}")
                print(f"Processed Documents: {batch_info[5]}")
                
                if batch_info[6]:  # config_snapshot
                    print(f"\nConfig Snapshot:")
                    try:
                        config = json.loads(batch_info[6]) if isinstance(batch_info[6], str) else batch_info[6]
                        print(json.dumps(config, indent=2))
                    except:
                        print(batch_info[6])
            
            main_cursor.close()
            main_conn.close()
            
        else:
            print("No entry found for batch 79")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_batch_79_full_error()