#!/usr/bin/env python3
"""
Check the current documents table schema
"""

import sys
sys.path.append('.')

from server.database import get_db_connection
import psycopg2

def check_documents_schema():
    """Check the current documents table schema"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print('📋 Current documents table schema:')
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'documents' AND table_schema = 'public'
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        for col in columns:
            print(f'  {col[0]}: {col[1]} (nullable: {col[2]}) default: {col[3]}')
        
        # Check if doc_id column exists
        doc_id_exists = any(col[0] == 'doc_id' for col in columns)
        valid_exists = any(col[0] == 'valid' for col in columns)
        
        print(f'\n🔍 Analysis:')
        print(f'  doc_id column exists: {doc_id_exists}')
        print(f'  valid column exists: {valid_exists}')

        # Also check docs table schema
        print(f'\n📋 Current docs table schema:')
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns
            WHERE table_name = 'docs' AND table_schema = 'public'
            ORDER BY ordinal_position;
        """)

        docs_columns = cursor.fetchall()
        for col in docs_columns:
            print(f'  {col[0]}: {col[1]} (nullable: {col[2]}) default: {col[3]}')

        # Check if document_id column exists in docs table
        document_id_exists = any(col[0] == 'document_id' for col in docs_columns)
        print(f'\n🔍 Docs table analysis:')
        print(f'  document_id column exists: {document_id_exists}')

        cursor.close()
        conn.close()

        return doc_id_exists, valid_exists
        
    except Exception as e:
        print(f'❌ Error: {e}')
        return False, False

if __name__ == "__main__":
    check_documents_schema()
