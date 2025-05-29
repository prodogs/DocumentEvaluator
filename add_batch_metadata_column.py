#!/usr/bin/env python3
"""
Add meta_data column to batches table

This script adds the meta_data JSON column to the batches table
for storing metadata that will be sent to the LLM during processing.
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

def add_meta_data_column():
    """Add meta_data column to batches table"""
    print("📋 Adding meta_data column to batches table...")
    
    add_column_sql = """
    -- Add meta_data column to batches table
    ALTER TABLE batches ADD COLUMN IF NOT EXISTS meta_data JSONB;
    
    -- Add comment for documentation
    COMMENT ON COLUMN batches.meta_data IS 'JSON metadata to be sent to LLM for context during document processing';
    """
    
    try:
        # Connect to PostgreSQL
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        # Execute the SQL
        cursor.execute(add_column_sql)
        conn.commit()
        
        print("✅ meta_data column added successfully")
        
        # Verify the column was added
        cursor.execute("""
            SELECT column_name, data_type, is_nullable 
            FROM information_schema.columns 
            WHERE table_name = 'batches' 
            AND column_name = 'meta_data';
        """)
        
        column_info = cursor.fetchone()
        if column_info:
            col_name, data_type, nullable = column_info
            print(f"📋 Column verified: {col_name}: {data_type} ({'NULL' if nullable == 'YES' else 'NOT NULL'})")
        else:
            print("❌ Column verification failed")
            return False
        
        cursor.close()
        conn.close()
        
        return True
        
    except psycopg2.Error as e:
        print(f"❌ Database error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

def check_column_exists():
    """Check if meta_data column already exists"""
    try:
        conn = psycopg2.connect(**DB_CONFIG)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.columns 
                WHERE table_schema = 'public' 
                AND table_name = 'batches'
                AND column_name = 'meta_data'
            );
        """)
        
        exists = cursor.fetchone()[0]
        cursor.close()
        conn.close()
        
        return exists
        
    except Exception as e:
        print(f"❌ Error checking column existence: {e}")
        return False

def main():
    """Main function"""
    print("🔧 Batch Meta Data Column Migration Script")
    print("=" * 50)
    
    # Check if column already exists
    if check_column_exists():
        print("ℹ️  meta_data column already exists in batches table")
        return True
    
    # Add the column
    if add_meta_data_column():
        print("\n🎉 Migration completed successfully!")
        print("   ✅ meta_data column added to batches table")
        print("   ✅ Column comment added for documentation")
        print("   ✅ Ready for JSON metadata storage")
        return True
    else:
        print("\n❌ Migration failed!")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
