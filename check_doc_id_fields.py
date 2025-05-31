#!/usr/bin/env python3
"""
Check doc_id field presence in docs and documents tables
"""

import sys
sys.path.append('./server')

from database import get_db_connection

def check_doc_id_fields():
    """Check doc_id field in both tables"""
    conn = get_db_connection()
    cursor = conn.cursor()
    
    print("🔍 Checking doc_id field presence in tables...\n")
    
    # Check documents table
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'documents' AND column_name = 'doc_id'
        AND table_schema = 'public';
    """)
    
    docs_table_doc_id = cursor.fetchall()
    
    # Check docs table  
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = 'docs' AND column_name = 'doc_id'
        AND table_schema = 'public';
    """)
    
    docs_table_doc_id_field = cursor.fetchall()
    
    print("📋 documents table doc_id field:")
    if docs_table_doc_id:
        for col in docs_table_doc_id:
            print(f"  ✅ Found: {col[0]} ({col[1]}, nullable: {col[2]}, default: {col[3]})")
    else:
        print("  ❌ NOT FOUND")
    
    print("\n📋 docs table doc_id field:")
    if docs_table_doc_id_field:
        for col in docs_table_doc_id_field:
            print(f"  ❌ Found (should not exist): {col[0]} ({col[1]}, nullable: {col[2]}, default: {col[3]})")
    else:
        print("  ✅ NOT FOUND (correct)")
    
    # Check all columns in both tables
    print("\n📋 All columns in documents table:")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'documents' AND table_schema = 'public'
        ORDER BY ordinal_position;
    """)
    
    for col in cursor.fetchall():
        print(f"  - {col[0]} ({col[1]}, nullable: {col[2]})")
    
    print("\n📋 All columns in docs table:")
    cursor.execute("""
        SELECT column_name, data_type, is_nullable
        FROM information_schema.columns 
        WHERE table_name = 'docs' AND table_schema = 'public'
        ORDER BY ordinal_position;
    """)
    
    for col in cursor.fetchall():
        print(f"  - {col[0]} ({col[1]}, nullable: {col[2]})")
    
    cursor.close()
    conn.close()
    
    # Summary
    print("\n" + "=" * 60)
    documents_has_doc_id = len(docs_table_doc_id) > 0
    docs_has_doc_id = len(docs_table_doc_id_field) > 0
    
    if documents_has_doc_id and not docs_has_doc_id:
        print("✅ CORRECT: documents table has doc_id, docs table does not")
        return True
    elif not documents_has_doc_id and not docs_has_doc_id:
        print("⚠️  ISSUE: Neither table has doc_id field")
        return False
    elif documents_has_doc_id and docs_has_doc_id:
        print("❌ ISSUE: Both tables have doc_id field (docs should not)")
        return False
    else:
        print("❌ ISSUE: docs table has doc_id but documents table does not")
        return False

if __name__ == "__main__":
    success = check_doc_id_fields()
    sys.exit(0 if success else 1)
