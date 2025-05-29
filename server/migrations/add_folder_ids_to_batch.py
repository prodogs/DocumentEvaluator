#!/usr/bin/env python3
"""
Database migration to add folder_ids JSON column to batches table.

This migration adds a new JSON column to store all folder IDs included in a batch,
allowing a single batch to represent processing of multiple folders.
"""

import sys
import os

# Add the project root to the Python path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

from sqlalchemy import text
from server.database import Session
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Add folder_ids JSON column to batches table."""

    session = Session()

    try:
        logger.info("Starting migration: Adding folder_ids column to batches table")

        # Check if column already exists
        check_column_sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'batches'
        AND column_name = 'folder_ids'
        AND table_schema = 'public';
        """

        result = session.execute(text(check_column_sql)).fetchone()

        if result:
            logger.info("Column 'folder_ids' already exists in batches table. Skipping migration.")
            return True

        # Add the new column
        add_column_sql = """
        ALTER TABLE batches
        ADD COLUMN folder_ids JSON;
        """

        session.execute(text(add_column_sql))
        session.commit()

        logger.info("Successfully added folder_ids JSON column to batches table")

        # Verify the column was added
        verify_sql = """
        SELECT column_name, data_type
        FROM information_schema.columns
        WHERE table_name = 'batches'
        AND column_name = 'folder_ids'
        AND table_schema = 'public';
        """

        result = session.execute(text(verify_sql)).fetchone()

        if result:
            logger.info(f"Verification successful: Column '{result[0]}' with type '{result[1]}' added")
            return True
        else:
            logger.error("Verification failed: Column was not added")
            return False

    except Exception as e:
        logger.error(f"Migration failed: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def rollback_migration():
    """Remove folder_ids column from batches table (rollback)."""

    session = Session()

    try:
        logger.info("Starting rollback: Removing folder_ids column from batches table")

        # Check if column exists
        check_column_sql = """
        SELECT column_name
        FROM information_schema.columns
        WHERE table_name = 'batches'
        AND column_name = 'folder_ids'
        AND table_schema = 'public';
        """

        result = session.execute(text(check_column_sql)).fetchone()

        if not result:
            logger.info("Column 'folder_ids' does not exist in batches table. Nothing to rollback.")
            return True

        # Remove the column
        drop_column_sql = """
        ALTER TABLE batches
        DROP COLUMN folder_ids;
        """

        session.execute(text(drop_column_sql))
        session.commit()

        logger.info("Successfully removed folder_ids column from batches table")
        return True

    except Exception as e:
        logger.error(f"Rollback failed: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Migrate batches table to add folder_ids JSON column")
    parser.add_argument("--rollback", action="store_true", help="Rollback the migration")

    args = parser.parse_args()

    if args.rollback:
        success = rollback_migration()
        if success:
            logger.info("Rollback completed successfully")
        else:
            logger.error("Rollback failed")
            sys.exit(1)
    else:
        success = run_migration()
        if success:
            logger.info("Migration completed successfully")
        else:
            logger.error("Migration failed")
            sys.exit(1)
