#!/usr/bin/env python3
"""
Fix Models Table - Add Missing is_globally_active Column

This script adds the missing is_globally_active column to the models table
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

def add_is_globally_active_column(cursor):
    """Add is_globally_active column to models table"""
    table_name = 'models'
    column_name = 'is_globally_active'
    
    if check_column_exists(cursor, table_name, column_name):
        logger.info(f"Column '{column_name}' already exists in '{table_name}' table")
        return True
    
    try:
        # Add the is_globally_active column with default value TRUE
        cursor.execute(f"""
            ALTER TABLE {table_name} 
            ADD COLUMN {column_name} BOOLEAN DEFAULT TRUE NOT NULL
        """)
        
        logger.info(f"Successfully added '{column_name}' column to '{table_name}' table")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add '{column_name}' column to '{table_name}' table: {e}")
        return False

def verify_column_addition(cursor):
    """Verify that the column was added successfully"""
    try:
        # Check if column exists and has correct properties
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'models' AND column_name = 'is_globally_active'
        """)
        
        result = cursor.fetchone()
        if result:
            column_name, data_type, is_nullable, column_default = result
            logger.info(f"Column verification:")
            logger.info(f"  Name: {column_name}")
            logger.info(f"  Type: {data_type}")
            logger.info(f"  Nullable: {is_nullable}")
            logger.info(f"  Default: {column_default}")
            
            # Check that all existing models have the default value
            cursor.execute("SELECT COUNT(*) FROM models WHERE is_globally_active = TRUE")
            active_count = cursor.fetchone()[0]
            
            cursor.execute("SELECT COUNT(*) FROM models")
            total_count = cursor.fetchone()[0]
            
            logger.info(f"Models with is_globally_active = TRUE: {active_count}/{total_count}")
            
            return True
        else:
            logger.error("Column verification failed - column not found")
            return False
            
    except Exception as e:
        logger.error(f"Column verification failed: {e}")
        return False

def main():
    """Main function to fix the models table"""
    logger.info("🔧 Fixing models table - adding is_globally_active column")
    
    try:
        # Connect to PostgreSQL database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # Start transaction
        cursor.execute("BEGIN")
        
        # Add the missing column
        success = add_is_globally_active_column(cursor)
        
        if success:
            # Verify the addition
            if verify_column_addition(cursor):
                # Commit transaction
                conn.commit()
                logger.info("✅ Successfully fixed models table!")
                logger.info("The is_globally_active column has been added to the models table.")
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
