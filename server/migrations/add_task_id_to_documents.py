#!/usr/bin/env python3
"""
Migration: Add task_id column to documents table

This migration adds a task_id column to the documents table to track
the LLM processing task associated with each document, enabling
service recovery on startup.
"""

import os
import sys
import sqlite3
import logging
from datetime import datetime

# Add the parent directory to the Python path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
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
    columns = cursor.fetchall()
    return any(column[1] == column_name for column in columns)

def add_task_id_column(db_path):
    """Add task_id column to documents table"""
    try:
        # Create backup first
        backup_path = backup_database(db_path)
        if not backup_path:
            logger.warning("Proceeding without backup (backup creation failed)")
        
        # Connect to database
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Check if task_id column already exists
        if check_column_exists(cursor, 'documents', 'task_id'):
            logger.info("task_id column already exists in documents table")
            conn.close()
            return True
        
        # Add task_id column
        logger.info("Adding task_id column to documents table...")
        cursor.execute("""
            ALTER TABLE documents 
            ADD COLUMN task_id TEXT
        """)
        
        # Create index on task_id for better performance
        logger.info("Creating index on task_id column...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_documents_task_id 
            ON documents(task_id)
        """)
        
        # Commit changes
        conn.commit()
        
        # Verify the column was added
        if check_column_exists(cursor, 'documents', 'task_id'):
            logger.info("✅ Successfully added task_id column to documents table")
            
            # Show updated schema
            cursor.execute("PRAGMA table_info(documents)")
            columns = cursor.fetchall()
            logger.info("Updated documents table schema:")
            for column in columns:
                logger.info(f"  {column[1]} {column[2]} {'NOT NULL' if column[3] else 'NULL'}")
            
            conn.close()
            return True
        else:
            logger.error("❌ Failed to add task_id column")
            conn.close()
            return False
            
    except sqlite3.Error as e:
        logger.error(f"Database error: {e}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return False

def main():
    """Main migration function"""
    logger.info("Starting migration: Add task_id column to documents table")
    
    # Get database path
    db_path = get_database_path()
    
    if not os.path.exists(db_path):
        logger.error(f"Database file not found: {db_path}")
        return 1
    
    logger.info(f"Using database: {db_path}")
    
    # Run migration
    success = add_task_id_column(db_path)
    
    if success:
        logger.info("✅ Migration completed successfully")
        return 0
    else:
        logger.error("❌ Migration failed")
        return 1

if __name__ == "__main__":
    sys.exit(main())
