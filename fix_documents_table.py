#!/usr/bin/env python3
"""
Fix Documents Table - Add Missing valid Column

This script adds the missing valid column to the documents table
in the PostgreSQL database.
"""

import sys
import os
import psycopg2
import logging

# Add server directory to path to import database configuration
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import get_db_connection

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

def check_column_exists(cursor, table_name, column_name):
    """Check if a column exists in a PostgreSQL table"""
    cursor.execute("""
        SELECT COUNT(*) 
        FROM information_schema.columns 
        WHERE table_name = %s AND column_name = %s
    """, (table_name, column_name))
    
    return cursor.fetchone()[0] > 0

def add_valid_column(cursor):
    """Add valid column to documents table"""
    table_name = 'documents'
    column_name = 'valid'
    
    if check_column_exists(cursor, table_name, column_name):
        logger.info(f"Column '{column_name}' already exists in '{table_name}' table")
        return True
    
    try:
        # Add the valid column with default value 'Y'
        cursor.execute(f"""
            ALTER TABLE {table_name} 
            ADD COLUMN {column_name} TEXT DEFAULT 'Y' NOT NULL
        """)
        
        logger.info(f"Successfully added '{column_name}' column to '{table_name}' table")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add '{column_name}' column to '{table_name}' table: {e}")
        return False

def add_task_id_column(cursor):
    """Add task_id column to documents table if missing"""
    table_name = 'documents'
    column_name = 'task_id'
    
    if check_column_exists(cursor, table_name, column_name):
        logger.info(f"Column '{column_name}' already exists in '{table_name}' table")
        return True
    
    try:
        # Add the task_id column
        cursor.execute(f"""
            ALTER TABLE {table_name} 
            ADD COLUMN {column_name} TEXT
        """)
        
        logger.info(f"Successfully added '{column_name}' column to '{table_name}' table")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add '{column_name}' column to '{table_name}' table: {e}")
        return False

def verify_columns(cursor):
    """Verify that the columns were added successfully"""
    try:
        # Check valid column
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'documents' AND column_name = 'valid'
        """)
        
        valid_result = cursor.fetchone()
        if valid_result:
            column_name, data_type, is_nullable, column_default = valid_result
            logger.info(f"Valid column verification:")
            logger.info(f"  Name: {column_name}")
            logger.info(f"  Type: {data_type}")
            logger.info(f"  Nullable: {is_nullable}")
            logger.info(f"  Default: {column_default}")
        else:
            logger.error("Valid column verification failed - column not found")
            return False
        
        # Check task_id column
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'documents' AND column_name = 'task_id'
        """)
        
        task_id_result = cursor.fetchone()
        if task_id_result:
            column_name, data_type, is_nullable, column_default = task_id_result
            logger.info(f"Task_id column verification:")
            logger.info(f"  Name: {column_name}")
            logger.info(f"  Type: {data_type}")
            logger.info(f"  Nullable: {is_nullable}")
            logger.info(f"  Default: {column_default}")
        else:
            logger.error("Task_id column verification failed - column not found")
            return False
        
        # Check that all existing documents have the default value
        cursor.execute("SELECT COUNT(*) FROM documents WHERE valid = 'Y'")
        valid_count = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM documents")
        total_count = cursor.fetchone()[0]
        
        logger.info(f"Documents with valid = 'Y': {valid_count}/{total_count}")
        
        return True
            
    except Exception as e:
        logger.error(f"Column verification failed: {e}")
        return False

def main():
    """Main function to fix the documents table"""
    logger.info("🔧 Fixing documents table - adding missing columns")
    
    try:
        # Connect to PostgreSQL database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("BEGIN")
        
        # Add the missing columns
        valid_success = add_valid_column(cursor)
        task_id_success = add_task_id_column(cursor)
        
        if valid_success and task_id_success:
            # Verify the additions
            if verify_columns(cursor):
                # Commit transaction
                conn.commit()
                logger.info("✅ Successfully fixed documents table!")
                logger.info("The valid and task_id columns have been added to the documents table.")
            else:
                conn.rollback()
                logger.error("❌ Column verification failed. Rolling back changes.")
                return False
        else:
            conn.rollback()
            logger.error("❌ Failed to add columns. Rolling back changes.")
            return False
            
    except Exception as e:
        logger.error(f"❌ Database error: {e}")
        if 'conn' in locals():
            conn.rollback()
        return False
        
    finally:
        if 'conn' in locals():
            cursor.close()
            conn.close()
    
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
