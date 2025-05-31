#!/usr/bin/env python3
"""
Fix Batches Table - Add Missing config_snapshot Column

This script adds the missing config_snapshot column to the batches table
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

def add_config_snapshot_column(cursor):
    """Add config_snapshot column to batches table"""
    table_name = 'batches'
    column_name = 'config_snapshot'
    
    if check_column_exists(cursor, table_name, column_name):
        logger.info(f"Column '{column_name}' already exists in '{table_name}' table")
        return True
    
    try:
        # Add the config_snapshot column as JSON
        cursor.execute(f"""
            ALTER TABLE {table_name} 
            ADD COLUMN {column_name} JSON DEFAULT '{{}}'::json
        """)
        
        logger.info(f"Successfully added '{column_name}' column to '{table_name}' table")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add '{column_name}' column to '{table_name}' table: {e}")
        return False

def verify_column(cursor):
    """Verify that the column was added successfully"""
    try:
        # Check config_snapshot column
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'batches' AND column_name = 'config_snapshot'
        """)
        
        result = cursor.fetchone()
        if result:
            column_name, data_type, is_nullable, column_default = result
            logger.info(f"Config_snapshot column verification:")
            logger.info(f"  Name: {column_name}")
            logger.info(f"  Type: {data_type}")
            logger.info(f"  Nullable: {is_nullable}")
            logger.info(f"  Default: {column_default}")
        else:
            logger.error("Config_snapshot column verification failed - column not found")
            return False
        
        # Check that all existing batches have the default value
        cursor.execute("SELECT COUNT(*) FROM batches")
        total_count = cursor.fetchone()[0]
        
        logger.info(f"Total batches in table: {total_count}")
        
        return True
            
    except Exception as e:
        logger.error(f"Column verification failed: {e}")
        return False

def main():
    """Main function to fix the batches table"""
    logger.info("🔧 Fixing batches table - adding missing config_snapshot column")
    
    try:
        # Connect to PostgreSQL database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("BEGIN")
        
        # Add the missing column
        success = add_config_snapshot_column(cursor)
        
        if success:
            # Verify the addition
            if verify_column(cursor):
                # Commit transaction
                conn.commit()
                logger.info("✅ Successfully fixed batches table!")
                logger.info("The config_snapshot column has been added to the batches table.")
            else:
                conn.rollback()
                logger.error("❌ Column verification failed. Rolling back changes.")
                return False
        else:
            conn.rollback()
            logger.error("❌ Failed to add column. Rolling back changes.")
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
