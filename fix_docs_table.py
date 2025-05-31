#!/usr/bin/env python3
"""
Fix Docs Table - Add Missing document_id Column

This script adds the missing document_id column to the docs table
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

def check_table_schema(cursor, table_name):
    """Check the schema of a table"""
    cursor.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns 
        WHERE table_name = %s
        ORDER BY ordinal_position
    """, (table_name,))
    
    return cursor.fetchall()

def add_document_id_column(cursor):
    """Add document_id column to docs table"""
    table_name = 'docs'
    column_name = 'document_id'
    
    if check_column_exists(cursor, table_name, column_name):
        logger.info(f"Column '{column_name}' already exists in '{table_name}' table")
        return True
    
    try:
        # Add the document_id column as foreign key
        cursor.execute(f"""
            ALTER TABLE {table_name} 
            ADD COLUMN {column_name} INTEGER REFERENCES documents(id)
        """)
        
        logger.info(f"Successfully added '{column_name}' column to '{table_name}' table")
        return True
        
    except Exception as e:
        logger.error(f"Failed to add '{column_name}' column to '{table_name}' table: {e}")
        return False

def verify_column(cursor):
    """Verify that the column was added successfully"""
    try:
        # Check document_id column
        cursor.execute("""
            SELECT column_name, data_type, is_nullable, column_default
            FROM information_schema.columns 
            WHERE table_name = 'docs' AND column_name = 'document_id'
        """)
        
        result = cursor.fetchone()
        if result:
            column_name, data_type, is_nullable, column_default = result
            logger.info(f"Document_id column verification:")
            logger.info(f"  Name: {column_name}")
            logger.info(f"  Type: {data_type}")
            logger.info(f"  Nullable: {is_nullable}")
            logger.info(f"  Default: {column_default}")
        else:
            logger.error("Document_id column verification failed - column not found")
            return False
        
        # Check that all existing docs have the column
        cursor.execute("SELECT COUNT(*) FROM docs")
        total_count = cursor.fetchone()[0]
        
        logger.info(f"Total docs in table: {total_count}")
        
        return True
            
    except Exception as e:
        logger.error(f"Column verification failed: {e}")
        return False

def main():
    """Main function to fix the docs table"""
    logger.info("🔧 Fixing docs table - checking and adding missing document_id column")
    
    try:
        # Connect to PostgreSQL database
        conn = get_db_connection()
        cursor = conn.cursor()
        
        # First, check current schema
        logger.info("📋 Current docs table schema:")
        schema = check_table_schema(cursor, 'docs')
        for row in schema:
            logger.info(f"  {row[0]}: {row[1]} (nullable: {row[2]}, default: {row[3]})")
        
        # Start transaction
        cursor.execute("BEGIN")
        
        # Add the missing column
        success = add_document_id_column(cursor)
        
        if success:
            # Verify the addition
            if verify_column(cursor):
                # Commit transaction
                conn.commit()
                logger.info("✅ Successfully fixed docs table!")
                logger.info("The document_id column has been added to the docs table.")
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
