#!/usr/bin/env python3
"""
Database migration script to add 'active' columns to prompts and llm_configurations tables.

This script adds:
- active column to prompts table (INTEGER, default 1, NOT NULL)
- active column to llm_configurations table (INTEGER, default 1, NOT NULL)

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

def add_active_column_to_prompts(cursor):
    """Add active column to prompts table"""
    table_name = 'prompts'
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

def add_active_column_to_llm_configurations(cursor):
    """Add active column to llm_configurations table"""
    table_name = 'llm_configurations'
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
        # Check prompts table
        cursor.execute("SELECT COUNT(*) FROM prompts WHERE active = 1")
        active_prompts = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM prompts")
        total_prompts = cursor.fetchone()[0]
        
        logger.info(f"Prompts table: {active_prompts}/{total_prompts} records are active")
        
        # Check llm_configurations table
        cursor.execute("SELECT COUNT(*) FROM llm_configurations WHERE active = 1")
        active_configs = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM llm_configurations")
        total_configs = cursor.fetchone()[0]
        
        logger.info(f"LLM Configurations table: {active_configs}/{total_configs} records are active")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify migration: {e}")
        return False

def main():
    """Main migration function"""
    logger.info("Starting database migration: Adding 'active' columns")
    
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
        
        # Add active column to prompts table
        success1 = add_active_column_to_prompts(cursor)
        
        # Add active column to llm_configurations table
        success2 = add_active_column_to_llm_configurations(cursor)
        
        if success1 and success2:
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
