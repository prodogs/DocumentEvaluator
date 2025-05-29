#!/usr/bin/env python3
"""
Migration: Add docs table and document metadata fields
- Creates new 'docs' table for storing encoded document content
- Adds doc_id foreign key to documents table
- Adds meta_data JSON field to documents table with default value
"""

import psycopg2
import sys
import os

# Database connection parameters
DB_HOST = "tablemini.local"
DB_NAME = "doc_eval"
DB_USER = "postgres"
DB_PASSWORD = "prodogs03"

def run_migration():
    """Execute the migration"""
    try:
        # Connect to database
        conn = psycopg2.connect(
            host=DB_HOST,
            database=DB_NAME,
            user=DB_USER,
            password=DB_PASSWORD
        )
        cursor = conn.cursor()
        
        print("🔄 Starting migration: Add docs table and document metadata...")
        
        # 1. Create docs table
        print("📝 Creating docs table...")
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS docs (
                id SERIAL PRIMARY KEY,
                content BYTEA NOT NULL,
                content_type TEXT,
                file_size INTEGER,
                encoding TEXT NOT NULL DEFAULT 'base64',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );
        """)
        
        # 2. Add doc_id column to documents table
        print("🔗 Adding doc_id column to documents table...")
        cursor.execute("""
            ALTER TABLE documents 
            ADD COLUMN IF NOT EXISTS doc_id INTEGER REFERENCES docs(id);
        """)
        
        # 3. Add meta_data column to documents table
        print("📊 Adding meta_data column to documents table...")
        cursor.execute("""
            ALTER TABLE documents 
            ADD COLUMN IF NOT EXISTS meta_data JSONB DEFAULT '{"meta_data": "NONE"}';
        """)
        
        # 4. Create indexes for performance
        print("⚡ Creating indexes...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_doc_id ON documents(doc_id);
        """)
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_meta_data ON documents USING GIN(meta_data);
        """)
        
        # Commit changes
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Verify the changes
        print("\n🔍 Verifying migration...")
        
        # Check docs table
        cursor.execute("SELECT COUNT(*) FROM information_schema.tables WHERE table_name = 'docs';")
        docs_table_exists = cursor.fetchone()[0] > 0
        print(f"   docs table exists: {docs_table_exists}")
        
        # Check doc_id column
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'documents' AND column_name = 'doc_id';
        """)
        doc_id_exists = cursor.fetchone()[0] > 0
        print(f"   documents.doc_id column exists: {doc_id_exists}")
        
        # Check meta_data column
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'documents' AND column_name = 'meta_data';
        """)
        meta_data_exists = cursor.fetchone()[0] > 0
        print(f"   documents.meta_data column exists: {meta_data_exists}")
        
        if docs_table_exists and doc_id_exists and meta_data_exists:
            print("✅ All migration changes verified successfully!")
        else:
            print("❌ Some migration changes may not have been applied correctly.")
            return False
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()
    
    return True

if __name__ == "__main__":
    success = run_migration()
    sys.exit(0 if success else 1)
