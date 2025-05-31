#!/usr/bin/env python3
"""
Migration: Add model_id column to connections table (PostgreSQL)

This migration adds a model_id column to the connections table to support
the new workflow where users select a model first, then a compatible provider.
This is the PostgreSQL version of the migration.
"""

import logging
import sys
import os

# Add the server directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import Session

logger = logging.getLogger(__name__)

def check_column_exists_postgresql(session, table_name, column_name):
    """Check if a column exists in a PostgreSQL table"""
    result = session.execute(text("""
        SELECT COUNT(*) as count 
        FROM information_schema.columns 
        WHERE table_name = :table_name 
        AND column_name = :column_name
    """), {"table_name": table_name, "column_name": column_name})
    return result.fetchone()[0] > 0

def add_model_id_to_connections():
    """Add model_id column to connections table"""
    session = Session()
    try:
        # Check if the column already exists
        if check_column_exists_postgresql(session, 'connections', 'model_id'):
            logger.info("model_id column already exists in connections table")
            return True
        
        logger.info("Adding model_id column to connections table...")
        
        # Add the model_id column
        session.execute(text("""
            ALTER TABLE connections 
            ADD COLUMN model_id INTEGER REFERENCES models(id)
        """))
        
        session.commit()
        
        # Verify the column was added
        if check_column_exists_postgresql(session, 'connections', 'model_id'):
            logger.info("✅ Successfully added model_id column to connections table")
            
            # Show updated schema
            result = session.execute(text("""
                SELECT column_name, data_type, is_nullable, column_default 
                FROM information_schema.columns 
                WHERE table_name = 'connections' 
                ORDER BY ordinal_position
            """))
            columns = result.fetchall()
            logger.info("Updated connections table schema:")
            for column in columns:
                logger.info(f"  {column[0]} {column[1]} {'NULL' if column[2] == 'YES' else 'NOT NULL'}")
            
            return True
        else:
            logger.error("❌ Failed to add model_id column")
            return False
            
    except Exception as e:
        logger.error(f"Error adding model_id column to connections table: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logger.info("Starting migration: Add model_id to connections table (PostgreSQL)")
    
    success = add_model_id_to_connections()
    
    if success:
        logger.info("✅ Migration completed successfully")
        sys.exit(0)
    else:
        logger.error("❌ Migration failed")
        sys.exit(1)
