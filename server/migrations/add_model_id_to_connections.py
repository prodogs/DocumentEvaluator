#!/usr/bin/env python3
"""
Migration: Add model_id column to connections table

This migration adds a model_id column to the connections table to support
the new workflow where users select a model first, then a compatible provider.
"""

import logging
import sys
import os

# Add the server directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import Session

logger = logging.getLogger(__name__)

def check_column_exists(session, table_name, column_name):
    """Check if a column exists in a table"""
    result = session.execute(text(f"""
        SELECT COUNT(*) as count 
        FROM pragma_table_info('{table_name}') 
        WHERE name = '{column_name}'
    """))
    return result.fetchone()[0] > 0

def add_model_id_to_connections():
    """Add model_id column to connections table"""
    session = Session()
    try:
        # Check if the column already exists
        if check_column_exists(session, 'connections', 'model_id'):
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
        if check_column_exists(session, 'connections', 'model_id'):
            logger.info("✅ Successfully added model_id column to connections table")
            
            # Show updated schema
            result = session.execute(text("PRAGMA table_info(connections)"))
            columns = result.fetchall()
            logger.info("Updated connections table schema:")
            for column in columns:
                logger.info(f"  {column[1]} {column[2]} {'NOT NULL' if column[3] else 'NULL'}")
            
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

def verify_migration():
    """Verify that the migration was successful"""
    session = Session()
    try:
        # Check that the column exists
        if not check_column_exists(session, 'connections', 'model_id'):
            logger.error("model_id column was not created")
            return False
        
        logger.info("Migration verification successful: model_id column exists in connections table")
        return True
        
    except Exception as e:
        logger.error(f"Failed to verify migration: {e}")
        return False
    finally:
        session.close()

def main():
    """Run the migration"""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(message)s'
    )
    
    logger.info("Starting migration: Add model_id to connections table")
    
    try:
        # Run the migration
        if add_model_id_to_connections():
            # Verify the migration
            if verify_migration():
                logger.info("✅ Migration completed successfully")
                return True
            else:
                logger.error("❌ Migration verification failed")
                return False
        else:
            logger.error("❌ Migration failed")
            return False
            
    except Exception as e:
        logger.error(f"Migration failed with error: {e}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
