#!/usr/bin/env python3
"""Clean up batch 70 documents from KnowledgeDocuments database"""

import psycopg2
import sys

def clean_batch_70_docs():
    """Remove any existing batch 70 documents from KnowledgeDocuments database"""
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
        
        # First, check what documents exist for batch 70
        print("Checking for existing batch 70 documents in KnowledgeDocuments database...")
        cursor.execute("""
            SELECT id, document_id, LENGTH(content) as content_length, file_size, created_at
            FROM docs
            WHERE document_id LIKE 'batch_70_%'
            ORDER BY created_at DESC
        """)
        
        docs = cursor.fetchall()
        print(f"\nFound {len(docs)} documents for batch 70:")
        
        for doc in docs:
            doc_id, document_id, content_length, file_size, created_at = doc
            print(f"  ID: {doc_id}, DocID: {document_id}, Content Length: {content_length}, File Size: {file_size}, Created: {created_at}")
            
            # Check if this is the problematic document
            if content_length == 1398101:
                print(f"    ⚠️ PROBLEMATIC DOCUMENT with invalid base64 length!")
        
        if docs:
            response = input("\nDo you want to delete these documents? (y/n): ")
            if response.lower() == 'y':
                # Delete the documents
                cursor.execute("""
                    DELETE FROM docs
                    WHERE document_id LIKE 'batch_70_%'
                """)
                deleted_count = cursor.rowcount
                conn.commit()
                print(f"\n✅ Deleted {deleted_count} documents from KnowledgeDocuments database")
            else:
                print("\n❌ Deletion cancelled")
        else:
            print("\nNo batch 70 documents found in KnowledgeDocuments database")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    clean_batch_70_docs()