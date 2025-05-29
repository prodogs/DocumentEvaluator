#!/usr/bin/env python3
"""
Database migration script to add 'llm_config_id' column to llm_responses table.

This script adds:
- llm_config_id column to llm_responses table (INTEGER, nullable, foreign key to llm_configurations.id)
- Populates the new column by matching existing llm_name values with llm_configurations.id

This provides a proper foreign key relationship to the full LLM configuration instead of just the name.
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

def add_llm_config_id_column(cursor):
    """Add llm_config_id column to llm_responses table and populate it"""
    table_name = 'llm_responses'
    column_name = 'llm_config_id'
    
    if check_column_exists(cursor, table_name, column_name):
        logger.info(f"Column '{column_name}' already exists in '{table_name}' table")
        return True
    
    try:
        # Add the llm_config_id column (nullable initially)
        cursor.execute(f"""
            ALTER TABLE {table_name} 
            ADD COLUMN {column_name} INTEGER
        """)
        logger.info(f"Added '{column_name}' column to '{table_name}' table")
        
        # Populate the new column by matching llm_name with llm_configurations.id
        cursor.execute("""
            UPDATE llm_responses 
            SET llm_config_id = (
                SELECT llm_configurations.id 
                FROM llm_configurations 
                WHERE llm_configurations.llm_name = llm_responses.llm_name
            )
            WHERE llm_responses.llm_name IS NOT NULL
        """)
        
        # Check how many records were updated
        cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE llm_config_id IS NOT NULL")
        updated_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM llm_responses")
        total_count = cursor.fetchone()[0]
        
        logger.info(f"Populated llm_config_id for {updated_count}/{total_count} records")
        
        # Check for any records that couldn't be matched
        cursor.execute("""
            SELECT DISTINCT llm_name 
            FROM llm_responses 
            WHERE llm_config_id IS NULL AND llm_name IS NOT NULL
        """)
        unmatched = cursor.fetchall()
        
        if unmatched:
            logger.warning(f"Could not match llm_config_id for llm_names: {[row[0] for row in unmatched]}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to add and populate '{column_name}' column in '{table_name}' table: {e}")
        return False

def verify_migration(cursor):
    """Verify that the migration was successful"""
    try:
        # Check that the column exists
        if not check_column_exists(cursor, 'llm_responses', 'llm_config_id'):
            logger.error("llm_config_id column was not created")
            return False
        
        # Check data integrity
        cursor.execute("""
            SELECT COUNT(*) 
            FROM llm_responses lr
            JOIN llm_configurations lc ON lr.llm_config_id = lc.id
            WHERE lr.llm_config_id IS NOT NULL
        """)
        valid_references = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE llm_config_id IS NOT NULL")
        total_with_config_id = cursor.fetchone()[0]
        
        if valid_references != total_with_config_id:
            logger.error(f"Data integrity issue: {valid_references} valid references vs {total_with_config_id} records with llm_config_id")
            return False
        
        logger.info(f"Migration verification successful: {valid_references} records have valid llm_config_id references")
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify migration: {e}")
        return False

def main():
    """Main migration function"""
    logger.info("Starting database migration: Adding 'llm_config_id' column to llm_responses")
    
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
        
        # Add and populate llm_config_id column
        success = add_llm_config_id_column(cursor)
        
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
