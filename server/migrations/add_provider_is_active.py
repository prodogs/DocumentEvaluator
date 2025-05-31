#!/usr/bin/env python3
"""
Migration: Add is_active field to llm_providers table

This migration adds the is_active field to the llm_providers table
and sets all existing providers to active by default.
"""

import os
import sys
import logging

# Add the parent directory to the path so we can import from server
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_connection

logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to add is_active field to llm_providers table"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Check if the column already exists
        cursor.execute("""
            SELECT column_name
            FROM information_schema.columns
            WHERE table_name = 'llm_providers' AND column_name = 'is_active'
        """)

        if cursor.fetchone():
            print("Column 'is_active' already exists in llm_providers table")
            return True

        print("Adding 'is_active' column to llm_providers table...")

        # Add the is_active column with default value True
        cursor.execute("""
            ALTER TABLE llm_providers
            ADD COLUMN is_active BOOLEAN DEFAULT TRUE NOT NULL
        """)

        # Update all existing providers to be active (this should be automatic with DEFAULT TRUE)
        cursor.execute("""
            UPDATE llm_providers
            SET is_active = TRUE
            WHERE is_active IS NULL
        """)

        conn.commit()
        print("✅ Successfully added 'is_active' column to llm_providers table")

        # Verify the migration
        cursor.execute("SELECT COUNT(*) FROM llm_providers WHERE is_active = TRUE")
        active_count = cursor.fetchone()[0]
        print(f"✅ Set {active_count} existing providers to active")

        return True

    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    print("Running migration: Add is_active field to llm_providers table")
    success = run_migration()
    if success:
        print("✅ Migration completed successfully")
        sys.exit(0)
    else:
        print("❌ Migration failed")
        sys.exit(1)
