#!/usr/bin/env python3
"""
Database migration script to add 'active' column to folders table.

This script adds:
- active column to folders table (INTEGER, default 1, NOT NULL)

Where:
- 0 = inactive/disabled
- 1 = active/enabled (default)
"""

import sqlite3
import os
import sys
import logging
from datetime import datetime

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def get_database_path():
    """Get the path to the database file"""
    # Try to find the database in the current directory or parent directory
    possible_paths = [
        'llm_evaluation.db',
        '../llm_evaluation.db',
        '../../llm_evaluation.db'
    ]
    
    for path in possible_paths:
        if os.path.exists(path):
            return path
    
    # If not found, use the default path
    return 'llm_evaluation.db'

def backup_database(db_path):
    """Create a backup of the database before migration"""
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    backup_path = f"{db_path}.backup_{timestamp}"
    
    try:
        import shutil
        shutil.copy2(db_path, backup_path)
        logger.info(f"Database backed up to: {backup_path}")
        return backup_path
    except Exception as e:
        logger.error(f"Failed to create backup: {e}")
        return None

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a table"""
    cursor.execute(f"PRAGMA table_info({table_name})")
    columns = [row[1] for row in cursor.fetchall()]
    return column_name in columns

def add_active_column_to_folders(cursor):
    """Add active column to folders table"""
    table_name = 'folders'
    column_name = 'active'
    
    if check_column_exists(cursor, table_name, column_name):
        logger.info(f"Column '{column_name}' already exists in '{table_name}' table")
        return True
    
    try:
        # Add the active column with default value 1 (active)
        cursor.execute(f"""
            ALTER TABLE {table_name} 
            ADD COLUMN {column_name} INTEGER DEFAULT 1 NOT NULL
        """)
        
        # Update all existing records to be active (1)
        cursor.execute(f"""
            UPDATE {table_name} 
            SET {column_name} = 1 
            WHERE {column_name} IS NULL
        """)
        
        logger.info(f"Successfully added '{column_name}' column to '{table_name}' table")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add '{column_name}' column to '{table_name}' table: {e}")
        return False

def verify_migration(cursor):
    """Verify that the migration was successful"""
    try:
        # Check folders table
        cursor.execute("SELECT COUNT(*) FROM folders WHERE active = 1")
        active_folders = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM folders")
        total_folders = cursor.fetchone()[0]
        
        logger.info(f"Folders table: {active_folders}/{total_folders} records are active")
        
        # Check that the column exists and has the right properties
        cursor.execute("PRAGMA table_info(folders)")
        columns = cursor.fetchall()
        active_column = None
        for col in columns:
            if col[1] == 'active':  # col[1] is column name
                active_column = col
                break
        
        if not active_column:
            logger.error("Active column was not created")
            return False
        
        # Check column properties: [cid, name, type, notnull, dflt_value, pk]
        if active_column[2] != 'INTEGER':
            logger.error(f"Active column type is {active_column[2]}, expected INTEGER")
            return False
        
        if active_column[3] != 1:  # notnull should be 1 (True)
            logger.error("Active column should be NOT NULL")
            return False
        
        if active_column[4] != '1':  # default value should be '1'
            logger.error(f"Active column default is {active_column[4]}, expected '1'")
            return False
        
        logger.info("Column properties verified: INTEGER, NOT NULL, DEFAULT 1")
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify migration: {e}")
        return False

def main():
    """Main migration function"""
    logger.info("Starting database migration: Adding 'active' column to folders table")
    
    # Get database path
    db_path = get_database_path()
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        sys.exit(1)
    
    logger.info(f"Using database: {db_path}")
    
    # Create backup
    backup_path = backup_database(db_path)
    if not backup_path:
        logger.warning("Proceeding without backup (not recommended)")
    
    # Connect to database
    try:
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("BEGIN TRANSACTION")
        
        # Add active column to folders table
        success = add_active_column_to_folders(cursor)
        
        if success:
            # Verify migration
            if verify_migration(cursor):
                # Commit transaction
                conn.commit()
                logger.info("Migration completed successfully!")
            else:
                conn.rollback()
                logger.error("Migration verification failed. Rolling back changes.")
                sys.exit(1)
        else:
            conn.rollback()
            logger.error("Migration failed. Rolling back changes.")
            sys.exit(1)
            
    except Exception as e:
        logger.error(f"Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
        sys.exit(1)
        
    finally:
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    main()
