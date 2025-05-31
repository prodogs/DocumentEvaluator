#!/usr/bin/env python3
"""
Migration: Add notes field to llm_providers table

This migration adds a notes field to the llm_providers table to allow users
to add custom notes about their LLM providers.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import Session, engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_provider_notes_field():
    """Add notes field to llm_providers table"""
    session = Session()
    
    try:
        # Check if the notes column already exists
        result = session.execute(text("""
            SELECT COUNT(*) as count 
            FROM pragma_table_info('llm_providers') 
            WHERE name = 'notes'
        """))
        
        column_exists = result.fetchone()[0] > 0
        
        if column_exists:
            logger.info("Notes column already exists in llm_providers table")
            return True
        
        # Add the notes column
        logger.info("Adding notes column to llm_providers table...")
        session.execute(text("""
            ALTER TABLE llm_providers 
            ADD COLUMN notes TEXT
        """))
        
        session.commit()
        logger.info("Successfully added notes column to llm_providers table")
        
        return True
        
    except Exception as e:
        logger.error(f"Error adding notes column: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("Starting migration: Add notes field to llm_providers table")
    
    success = add_provider_notes_field()
    
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
        sys.exit(1)
