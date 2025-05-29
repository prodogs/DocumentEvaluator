#!/usr/bin/env python3
"""
Create batch_archive table in PostgreSQL database

This script creates the batch_archive table for storing archived batch data
when batches are deleted from the main tables.
"""

import psycopg2
import sys
from datetime import datetime

# Database connection parameters
DB_CONFIG = {
    'host': 'tablemini.local',
    'database': 'doc_eval',
    'user': 'postgres',
    'password': 'prodogs03',
    'port': 5432
}

def create_batch_archive_table():
    """Create the batch_archive table"""
    print("📋 Creating batch_archive table...")

    create_table_sql = """
    CREATE TABLE IF NOT EXISTS batch_archive (
        id SERIAL PRIMARY KEY,
        original_batch_id INTEGER NOT NULL,
        batch_number INTEGER NOT NULL,
        batch_name TEXT,
        archived_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        archived_by TEXT,
        archive_reason TEXT DEFAULT 'Manual deletion',
        batch_data JSONB NOT NULL,
        documents_data JSONB NOT NULL,
        llm_responses_data JSONB NOT NULL,
        archive_metadata JSONB
    );

    -- Create indexes for better query performance
    CREATE INDEX IF NOT EXISTS idx_batch_archive_original_batch_id ON batch_archive(original_batch_id);
    CREATE INDEX IF NOT EXISTS idx_batch_archive_batch_number ON batch_archive(batch_number);
    CREATE INDEX IF NOT EXISTS idx_batch_archive_archived_at ON batch_archive(archived_at);

    -- Add comments for documentation
    COMMENT ON TABLE batch_archive IS 'Archive table for storing deleted batch data';
    COMMENT ON COLUMN batch_archive.original_batch_id IS 'Original batch ID before deletion';
    COMMENT ON COLUMN batch_archive.batch_number IS 'Original batch number';
    COMMENT ON COLUMN batch_archive.batch_data IS 'Complete batch record as JSON';
    COMMENT ON COLUMN batch_archive.documents_data IS 'All associated documents as JSON array';
    COMMENT ON COLUMN batch_archive.llm_responses_data IS 'All associated LLM responses as JSON array';
    COMMENT ON COLUMN batch_archive.archive_metadata IS 'Additional metadata like counts and statistics';
    """

    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Execute the SQL
        cursor.execute(create_table_sql)
        conn.commit()

        print("✅ batch_archive table created successfully")

        # Verify the table was created
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns
            WHERE table_name = 'batch_archive'
            ORDER BY ordinal_position;
        """)

        columns = cursor.fetchall()
        print(f"📋 Table structure:")
        for col_name, data_type, nullable in columns:
            print(f"   {col_name}: {data_type} ({'NULL' if nullable == 'YES' else 'NOT NULL'})")

        cursor.close()
        conn.close()

        return True

    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_table_exists():
    """Check if batch_archive table already exists"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables
                WHERE table_schema = 'public'
                AND table_name = 'batch_archive'
            );
        """)

        exists = cursor.fetchone()[0]
        cursor.close()
        conn.close()

        return exists

    except Exception as e:
        print(f"❌ Error checking table existence: {e}")
        return False

def main():
    """Main function"""
    print("🗃️  Batch Archive Table Creation Script")
    print("=" * 50)

    # Check if table already exists
    if check_table_exists():
        print("ℹ️  batch_archive table already exists")
        return True

    # Create the table
    if create_batch_archive_table():
        print("\n🎉 Migration completed successfully!")
        print("   ✅ batch_archive table created")
        print("   ✅ Indexes created for performance")
        print("   ✅ Comments added for documentation")
        return True
    else:
        print("\n❌ Migration failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
