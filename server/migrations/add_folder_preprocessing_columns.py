#!/usr/bin/env python3
"""
Migration: Add folder preprocessing columns
- Add 'valid' column to documents table
- Add 'file_size' column to docs table
- Add 'status' column to folders table for preprocessing status
"""

import psycopg2
import sys
import os

# Add the parent directory to the path so we can import database
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from database import get_db_connection

def run_migration():
    """Add columns for folder preprocessing workflow"""

    conn = None
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        print("🔄 Starting folder preprocessing migration...")

        # 1. Add 'valid' column to documents table
        print("📄 Adding 'valid' column to documents table...")
        try:
            cursor.execute("""
                ALTER TABLE documents
                ADD COLUMN valid VARCHAR(1) DEFAULT 'Y' CHECK (valid IN ('Y', 'N'))
            """)
            conn.commit()
            print("✅ Added 'valid' column to documents table")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
            print("ℹ️  'valid' column already exists in documents table")
        except Exception as e:
            conn.rollback()
            print(f"⚠️  Error adding 'valid' column: {e}")

        # 2. Add 'file_size' column to docs table
        print("📁 Adding 'file_size' column to docs table...")
        try:
            cursor.execute("""
                ALTER TABLE docs
                ADD COLUMN file_size INTEGER DEFAULT 0
            """)
            conn.commit()
            print("✅ Added 'file_size' column to docs table")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
            print("ℹ️  'file_size' column already exists in docs table")
        except Exception as e:
            conn.rollback()
            print(f"⚠️  Error adding 'file_size' column: {e}")

        # 3. Add 'status' column to folders table for preprocessing status
        print("📂 Adding 'status' column to folders table...")
        try:
            cursor.execute("""
                ALTER TABLE folders
                ADD COLUMN status VARCHAR(20) DEFAULT 'NOT_PROCESSED'
                CHECK (status IN ('NOT_PROCESSED', 'PREPROCESSING', 'READY', 'ERROR'))
            """)
            conn.commit()
            print("✅ Added 'status' column to folders table")
        except psycopg2.errors.DuplicateColumn:
            conn.rollback()
            print("ℹ️  'status' column already exists in folders table")
        except Exception as e:
            conn.rollback()
            print(f"⚠️  Error adding 'status' column: {e}")

        # 4. Create index on valid column for performance
        print("🔍 Creating index on documents.valid column...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_documents_valid
                ON documents(valid)
            """)
            conn.commit()
            print("✅ Created index on documents.valid")
        except Exception as e:
            conn.rollback()
            print(f"ℹ️  Index creation note: {e}")

        # 5. Create index on folder status for performance
        print("🔍 Creating index on folders.status column...")
        try:
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_folders_status
                ON folders(status)
            """)
            conn.commit()
            print("✅ Created index on folders.status")
        except Exception as e:
            conn.rollback()
            print(f"ℹ️  Index creation note: {e}")

        # 6. Update existing documents to have valid='Y' by default
        print("🔄 Updating existing documents to valid='Y'...")
        try:
            cursor.execute("""
                UPDATE documents
                SET valid = 'Y'
                WHERE valid IS NULL
            """)
            updated_docs = cursor.rowcount
            conn.commit()
            print(f"✅ Updated {updated_docs} existing documents to valid='Y'")
        except Exception as e:
            conn.rollback()
            print(f"⚠️  Error updating documents: {e}")

        # 7. Update existing folders to status='READY' (assuming they're already processed)
        print("🔄 Updating existing folders to status='READY'...")
        try:
            cursor.execute("""
                UPDATE folders
                SET status = 'READY'
                WHERE status IS NULL OR status = 'NOT_PROCESSED'
            """)
            updated_folders = cursor.rowcount
            conn.commit()
            print(f"✅ Updated {updated_folders} existing folders to status='READY'")
        except Exception as e:
            conn.rollback()
            print(f"⚠️  Error updating folders: {e}")

        print("🎉 Folder preprocessing migration completed!")

        # Show summary
        print("\n📊 Migration Summary:")
        print("  ✅ documents.valid column (Y/N validation flag)")
        print("  ✅ docs.file_size column (file size in bytes)")
        print("  ✅ folders.status column (preprocessing status)")
        print("  ✅ Performance indexes created")
        print("  ✅ Existing data updated")

    except Exception as e:
        if conn:
            conn.rollback()
        print(f"❌ Migration failed: {e}")
        raise
    finally:
        if conn:
            cursor.close()
            conn.close()

if __name__ == "__main__":
    run_migration()
