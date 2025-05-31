#!/usr/bin/env python3
"""
Check if doc_id is properly set after staging
"""

import sys
sys.path.append('.')

from server.database import get_db_connection
import psycopg2

def check_doc_id_after_staging():
    """Check if documents have proper doc_id values after staging"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print('🔍 Checking doc_id values in documents table after staging...\n')
        
        # Get documents from the latest batch (batch #7)
        cursor.execute("""
            SELECT d.id, d.filename, d.doc_id, d.batch_id, b.batch_number
            FROM documents d
            LEFT JOIN batches b ON d.batch_id = b.id
            WHERE b.batch_number = 7
            ORDER BY d.id;
        """)
        
        documents = cursor.fetchall()
        
        if not documents:
            print("❌ No documents found in batch #7")
            return False
        
        print(f"📊 Found {len(documents)} documents in batch #7:")
        print("ID | Filename | doc_id | batch_id | batch_number")
        print("-" * 80)
        
        all_have_doc_id = True
        for doc in documents:
            doc_id, filename, doc_id_value, batch_id, batch_number = doc
            status = "✅" if doc_id_value is not None else "❌"
            doc_id_str = str(doc_id_value) if doc_id_value is not None else "NULL"
            print(f"{doc_id:2} | {filename[:30]:30} | {doc_id_str:6} | {batch_id:8} | {batch_number}")
            if doc_id_value is None:
                all_have_doc_id = False
        
        print("\n" + "=" * 80)
        
        if all_have_doc_id:
            print("🎉 SUCCESS: All documents have doc_id values set!")
        else:
            print("❌ ISSUE: Some documents are missing doc_id values")
        
        # Also check if the docs table has corresponding entries
        print(f"\n🔍 Checking docs table for corresponding entries...")
        cursor.execute("""
            SELECT docs.id, docs.document_id, d.filename
            FROM docs
            LEFT JOIN documents d ON docs.document_id = d.id
            WHERE d.batch_id = (SELECT id FROM batches WHERE batch_number = 7)
            ORDER BY docs.id;
        """)
        
        docs_entries = cursor.fetchall()
        print(f"📊 Found {len(docs_entries)} entries in docs table for batch #7:")
        print("docs.id | document_id | filename")
        print("-" * 50)
        
        for entry in docs_entries:
            docs_id, document_id, filename = entry
            print(f"{docs_id:7} | {document_id:11} | {filename[:30]}")
        
        cursor.close()
        conn.close()
        
        return all_have_doc_id
        
    except Exception as e:
        print(f'❌ Error: {e}')
        return False

if __name__ == "__main__":
    success = check_doc_id_after_staging()
    sys.exit(0 if success else 1)
