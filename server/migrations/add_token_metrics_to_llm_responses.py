#!/usr/bin/env python3
"""
Migration: Add token metrics columns to llm_responses table

This migration adds the missing token and timing metrics columns to the llm_responses table
to support the enhanced analyze_status response that includes:
- input_tokens: Number of input tokens sent to the LLM
- output_tokens: Number of output tokens received from the LLM  
- time_taken_seconds: Time taken for the LLM call in seconds
- tokens_per_second: Rate of tokens per second

These fields are part of the OpenAPI specification but were missing from the database schema.
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

def add_token_metrics_columns():
    """Add token metrics columns to llm_responses table"""
    session = Session()
    try:
        columns_to_add = [
            ('input_tokens', 'INTEGER'),
            ('output_tokens', 'INTEGER'), 
            ('time_taken_seconds', 'REAL'),
            ('tokens_per_second', 'REAL')
        ]
        
        columns_added = []
        
        for column_name, column_type in columns_to_add:
            # Check if the column already exists
            if check_column_exists(session, 'llm_responses', column_name):
                logger.info(f"{column_name} column already exists in llm_responses table")
                continue
            
            logger.info(f"Adding {column_name} column to llm_responses table...")
            
            # Add the column
            session.execute(text(f"""
                ALTER TABLE llm_responses 
                ADD COLUMN {column_name} {column_type}
            """))
            
            columns_added.append(column_name)
        
        if columns_added:
            session.commit()
            logger.info(f"✅ Successfully added columns: {', '.join(columns_added)}")
        else:
            logger.info("✅ All token metrics columns already exist")
        
        # Verify all columns were added
        missing_columns = []
        for column_name, _ in columns_to_add:
            if not check_column_exists(session, 'llm_responses', column_name):
                missing_columns.append(column_name)
        
        if missing_columns:
            logger.error(f"❌ Failed to add columns: {', '.join(missing_columns)}")
            return False
        
        # Show updated schema
        result = session.execute(text("PRAGMA table_info(llm_responses)"))
        columns = result.fetchall()
        logger.info("Updated llm_responses table schema:")
        for column in columns:
            logger.info(f"  {column[1]} {column[2]} {'NOT NULL' if column[3] else 'NULL'}")
        
        return True
            
    except Exception as e:
        logger.error(f"Error adding token metrics columns to llm_responses table: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def verify_migration():
    """Verify that the migration was successful"""
    session = Session()
    try:
        required_columns = ['input_tokens', 'output_tokens', 'time_taken_seconds', 'tokens_per_second']
        
        for column_name in required_columns:
            if not check_column_exists(session, 'llm_responses', column_name):
                logger.error(f"{column_name} column was not created")
                return False
        
        logger.info("Migration verification successful: all token metrics columns exist in llm_responses table")
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
    
    logger.info("Starting migration: Add token metrics columns to llm_responses table")
    
    try:
        # Run the migration
        if add_token_metrics_columns():
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
