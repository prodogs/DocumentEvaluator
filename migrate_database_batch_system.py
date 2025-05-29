#!/usr/bin/env python3
"""
Database Migration Script for Batch System

This script adds the batch system tables and columns to the existing database:
1. Creates the 'batches' table
2. Adds 'batch_id' column to the 'documents' table
3. Handles existing data gracefully
"""

import sys
import sqlite3
import os
from datetime import datetime

sys.path.append('.')

def get_database_path():
    """Get the database path from the application"""
    try:
        from server.database import DATABASE_URL
        # Extract path from SQLite URL (sqlite:///path/to/db.db)
        if DATABASE_URL.startswith('sqlite:///'):
            return DATABASE_URL[10:]  # Remove 'sqlite:///'
        elif DATABASE_URL.startswith('sqlite://'):
            return DATABASE_URL[9:]   # Remove 'sqlite://'
        else:
            return 'llm_evaluation.db'
    except ImportError:
        # Fallback to default path
        return 'llm_evaluation.db'

def backup_database(db_path):
    """Create a backup of the database before migration"""
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        return None

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = f"{db_path}.backup_{timestamp}"

    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        print(f"✅ Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        print(f"❌ Failed to backup database: {e}")
        return None

def check_existing_schema(cursor):
    """Check what tables and columns already exist"""
    print("🔍 Checking existing database schema...")

    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = [row[0] for row in cursor.fetchall()]

    print(f"📋 Existing tables: {tables}")

    # Check if batches table exists
    batches_exists = 'batches' in tables

    # Check documents table structure
    documents_columns = []
    if 'documents' in tables:
        cursor.execute("PRAGMA table_info(documents);")
        documents_columns = [row[1] for row in cursor.fetchall()]
        print(f"📋 Documents table columns: {documents_columns}")

    batch_id_exists = 'batch_id' in documents_columns
    task_id_exists = 'task_id' in documents_columns

    return {
        'batches_table_exists': batches_exists,
        'batch_id_column_exists': batch_id_exists,
        'task_id_column_exists': task_id_exists,
        'documents_table_exists': 'documents' in tables,
        'documents_columns': documents_columns
    }

def create_batches_table(cursor):
    """Create the batches table"""
    print("📊 Creating batches table...")

    create_batches_sql = """
    CREATE TABLE batches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        batch_number INTEGER UNIQUE NOT NULL,
        batch_name TEXT,
        description TEXT,
        folder_path TEXT,
        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
        started_at DATETIME,
        completed_at DATETIME,
        status TEXT DEFAULT 'P' NOT NULL,
        total_documents INTEGER DEFAULT 0,
        processed_documents INTEGER DEFAULT 0
    );
    """

    try:
        cursor.execute(create_batches_sql)
        print("✅ Batches table created successfully")
        return True
    except Exception as e:
        print(f"❌ Failed to create batches table: {e}")
        return False

def add_batch_id_column(cursor):
    """Add batch_id column to documents table"""
    print("📄 Adding batch_id column to documents table...")

    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN batch_id INTEGER;")
        print("✅ batch_id column added to documents table")
        return True
    except Exception as e:
        print(f"❌ Failed to add batch_id column: {e}")
        return False

def add_task_id_column(cursor):
    """Add task_id column to documents table"""
    print("📄 Adding task_id column to documents table...")

    try:
        cursor.execute("ALTER TABLE documents ADD COLUMN task_id TEXT;")
        print("✅ task_id column added to documents table")
        return True
    except Exception as e:
        print(f"❌ Failed to add task_id column: {e}")
        return False

def create_default_batch(cursor):
    """Create a default batch for existing documents"""
    print("📦 Creating default batch for existing documents...")

    try:
        # Check if there are any existing documents without batch_id
        cursor.execute("SELECT COUNT(*) FROM documents WHERE batch_id IS NULL;")
        doc_count = cursor.fetchone()[0]

        if doc_count > 0:
            # Check if default batch already exists
            cursor.execute("SELECT id FROM batches WHERE batch_name = 'Legacy Documents';")
            existing_batch = cursor.fetchone()

            if existing_batch:
                batch_id = existing_batch[0]
                print(f"ℹ️  Using existing default batch (ID: {batch_id})")
            else:
                # Get the next available batch number
                cursor.execute("SELECT COALESCE(MAX(batch_number), 0) + 1 FROM batches;")
                next_batch_number = cursor.fetchone()[0]

                # Create a default batch
                cursor.execute("""
                    INSERT INTO batches (batch_number, batch_name, description, status, started_at)
                    VALUES (?, 'Legacy Documents', 'Default batch for documents created before batch system', 'C', CURRENT_TIMESTAMP);
                """, (next_batch_number,))

                # Get the batch ID
                batch_id = cursor.lastrowid
                print(f"✅ Created default batch (ID: {batch_id}, Number: {next_batch_number})")

            # Update all existing documents to use this batch
            cursor.execute("UPDATE documents SET batch_id = ? WHERE batch_id IS NULL;", (batch_id,))

            updated_count = cursor.rowcount
            print(f"✅ Linked {updated_count} existing documents to default batch")
            return True
        else:
            print("ℹ️  No existing documents without batch_id found, skipping default batch creation")
            return True

    except Exception as e:
        print(f"❌ Failed to create default batch: {e}")
        return False

def verify_migration(cursor):
    """Verify that the migration was successful"""
    print("🔍 Verifying migration...")

    try:
        # Check batches table
        cursor.execute("SELECT COUNT(*) FROM batches;")
        batch_count = cursor.fetchone()[0]
        print(f"✅ Batches table accessible, contains {batch_count} batches")

        # Check documents table with batch_id
        cursor.execute("SELECT COUNT(*) FROM documents WHERE batch_id IS NOT NULL;")
        docs_with_batch = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM documents;")
        total_docs = cursor.fetchone()[0]

        print(f"✅ Documents table accessible, {docs_with_batch}/{total_docs} documents have batch_id")

        # Test a join query
        cursor.execute("""
            SELECT d.filename, b.batch_name
            FROM documents d
            LEFT JOIN batches b ON d.batch_id = b.id
            LIMIT 5;
        """)

        results = cursor.fetchall()
        print(f"✅ Join query successful, sample results: {len(results)} rows")

        return True

    except Exception as e:
        print(f"❌ Migration verification failed: {e}")
        return False

def run_migration():
    """Run the complete database migration"""
    print("🚀 Starting Database Migration for Batch System\n")

    # Get database path
    db_path = get_database_path()
    print(f"📍 Database path: {db_path}")

    # Check if database exists
    if not os.path.exists(db_path):
        print(f"❌ Database file not found: {db_path}")
        print("💡 Make sure the application has been run at least once to create the database")
        return False

    # Backup database
    backup_path = backup_database(db_path)
    if not backup_path:
        print("⚠️  Proceeding without backup (risky!)")

    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()

        # Check existing schema
        schema_info = check_existing_schema(cursor)

        migration_needed = False

        # Create batches table if it doesn't exist
        if not schema_info['batches_table_exists']:
            if not create_batches_table(cursor):
                return False
            migration_needed = True
        else:
            print("ℹ️  Batches table already exists")

        # Add batch_id column if it doesn't exist
        if not schema_info['batch_id_column_exists']:
            if not add_batch_id_column(cursor):
                return False
            migration_needed = True
        else:
            print("ℹ️  batch_id column already exists")

        # Add task_id column if it doesn't exist
        if not schema_info['task_id_column_exists']:
            if not add_task_id_column(cursor):
                return False
            migration_needed = True
        else:
            print("ℹ️  task_id column already exists")

        # Create default batch for existing documents
        if migration_needed:
            if not create_default_batch(cursor):
                return False

        # Commit changes
        conn.commit()

        # Verify migration
        if not verify_migration(cursor):
            return False

        print(f"\n🎉 Migration completed successfully!")
        print(f"   ✅ Batches table created/verified")
        print(f"   ✅ batch_id column added/verified")
        print(f"   ✅ Existing documents linked to default batch")
        print(f"   ✅ Database schema updated for batch system")

        if backup_path:
            print(f"   💾 Backup available at: {backup_path}")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

def rollback_migration():
    """Rollback the migration (restore from backup)"""
    print("🔄 Rolling back migration...")

    db_path = get_database_path()

    # Find the most recent backup
    import glob
    backup_pattern = f"{db_path}.backup_*"
    backups = glob.glob(backup_pattern)

    if not backups:
        print("❌ No backup files found for rollback")
        return False

    # Get the most recent backup
    latest_backup = max(backups, key=os.path.getctime)

    try:
        import shutil
        shutil.copy2(latest_backup, db_path)
        print(f"✅ Database restored from backup: {latest_backup}")
        return True
    except Exception as e:
        print(f"❌ Rollback failed: {e}")
        return False

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        success = rollback_migration()
    else:
        success = run_migration()

    if success:
        print(f"\n✅ Operation completed successfully!")
        print(f"💡 You can now use the batch system features")
    else:
        print(f"\n❌ Operation failed!")
        print(f"💡 Check the error messages above and try again")
        if len(sys.argv) <= 1 or sys.argv[1] != "rollback":
            print(f"💡 You can rollback with: python {sys.argv[0]} rollback")

    sys.exit(0 if success else 1)
