#!/usr/bin/env python3
"""
Migration: Add document_id foreign key to docs table
"""

import psycopg2
import sys
import os

# Add the parent directory to the path so we can import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection

def run_migration():
    """Add document_id foreign key to docs table"""
    
    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        
        print("🔄 Adding document_id column to docs table...")
        
        # Add document_id column
        try:
            cursor.execute("""
                ALTER TABLE docs 
                ADD COLUMN document_id INTEGER
            """)
            conn.commit()
            print("✅ Added document_id column to docs table")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
            print("ℹ️  document_id column already exists in docs table")
        except Exception as e:
            conn.rollback()
            print(f"⚠️  Error adding document_id column: {e}")
        
        # Add foreign key constraint
        try:
            cursor.execute("""
                ALTER TABLE docs 
                ADD CONSTRAINT fk_docs_document_id 
                FOREIGN KEY (document_id) REFERENCES documents(id) ON DELETE CASCADE
            """)
            conn.commit()
            print("✅ Added foreign key constraint for document_id")
        except psycopg2.errors.DuplicateObject:
            conn.rollback()
            print("ℹ️  Foreign key constraint already exists")
        except Exception as e:
            conn.rollback()
            print(f"⚠️  Error adding foreign key constraint: {e}")
        
        # Create index for performance
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_docs_document_id 
                ON docs(document_id)
            """)
            conn.commit()
            print("✅ Created index on docs.document_id")
        except Exception as e:
            conn.rollback()
            print(f"⚠️  Error creating index: {e}")
        
        print("🎉 Migration completed!")
        
    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        if conn:
            conn.close()

if __name__ == "__main__":
    run_migration()
