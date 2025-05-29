#!/usr/bin/env python3
"""
Migration: Add doc_type column to docs table
- Adds doc_type column to store document type/extension
- Populates existing records with doc_type based on content_type
"""

import psycopg2
import sys

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
        
        print("🔄 Starting migration: Add doc_type column to docs table...")
        
        # 1. Add doc_type column
        print("📝 Adding doc_type column...")
        cursor.execute("""
            ALTER TABLE docs 
            ADD COLUMN IF NOT EXISTS doc_type TEXT;
        """)
        
        # 2. Populate doc_type for existing records based on content_type
        print("🔄 Populating doc_type for existing records...")
        
        # Map common MIME types to document types
        mime_to_doc_type = {
            'application/pdf': 'pdf',
            'application/msword': 'doc',
            'application/vnd.openxmlformats-officedocument.wordprocessingml.document': 'docx',
            'text/plain': 'txt',
            'text/rtf': 'rtf',
            'application/rtf': 'rtf',
            'application/vnd.oasis.opendocument.text': 'odt',
            'application/vnd.ms-excel': 'xls',
            'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': 'xlsx',
            'text/csv': 'csv',
            'application/vnd.ms-powerpoint': 'ppt',
            'application/vnd.openxmlformats-officedocument.presentationml.presentation': 'pptx',
            'image/jpeg': 'jpg',
            'image/png': 'png',
            'image/gif': 'gif',
            'image/bmp': 'bmp',
            'image/tiff': 'tiff',
            'text/html': 'html',
            'application/xml': 'xml',
            'application/json': 'json',
            'text/markdown': 'md'
        }
        
        # Update records with known MIME types
        for mime_type, doc_type in mime_to_doc_type.items():
            cursor.execute("""
                UPDATE docs 
                SET doc_type = %s 
                WHERE content_type = %s AND doc_type IS NULL;
            """, (doc_type, mime_type))
            updated_count = cursor.rowcount
            if updated_count > 0:
                print(f"   Updated {updated_count} records: {mime_type} -> {doc_type}")
        
        # Handle generic cases
        cursor.execute("""
            UPDATE docs 
            SET doc_type = 'unknown' 
            WHERE doc_type IS NULL;
        """)
        unknown_count = cursor.rowcount
        if unknown_count > 0:
            print(f"   Set {unknown_count} records to 'unknown' doc_type")
        
        # 3. Create index for performance
        print("⚡ Creating index on doc_type...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_docs_doc_type ON docs(doc_type);
        """)
        
        # Commit changes
        conn.commit()
        print("✅ Migration completed successfully!")
        
        # Verify the changes
        print("\n🔍 Verifying migration...")
        
        # Check doc_type column exists
        cursor.execute("""
            SELECT COUNT(*) FROM information_schema.columns 
            WHERE table_name = 'docs' AND column_name = 'doc_type';
        """)
        doc_type_exists = cursor.fetchone()[0] > 0
        print(f"   docs.doc_type column exists: {doc_type_exists}")
        
        # Check doc_type distribution
        cursor.execute("""
            SELECT doc_type, COUNT(*) as count 
            FROM docs 
            GROUP BY doc_type 
            ORDER BY count DESC;
        """)
        doc_type_stats = cursor.fetchall()
        print("   Document type distribution:")
        for doc_type, count in doc_type_stats:
            print(f"     {doc_type}: {count} documents")
        
        if doc_type_exists:
            print("✅ Migration verified successfully!")
        else:
            print("❌ Migration verification failed.")
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
