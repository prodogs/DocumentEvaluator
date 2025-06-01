#!/usr/bin/env python3
"""
Fix SQLAlchemy metadata cache issue by forcing table reflection
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Base, engine, Session
from sqlalchemy import MetaData, Table
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def fix_metadata_cache():
    """Force SQLAlchemy to refresh metadata from database"""
    try:
        logger.info("🔄 Clearing SQLAlchemy metadata cache...")
        
        # Clear the existing metadata
        Base.metadata.clear()
        
        # Create new metadata and reflect from database
        metadata = MetaData()
        metadata.reflect(bind=engine)
        
        # Check what columns actually exist in llm_responses table
        if 'llm_responses' in metadata.tables:
            llm_responses_table = metadata.tables['llm_responses']
            logger.info("📋 Actual llm_responses table columns:")
            for column in llm_responses_table.columns:
                logger.info(f"   - {column.name} ({column.type})")
                
            # Check if deprecated columns exist
            deprecated_columns = ['llm_config_id', 'llm_name']
            for col in deprecated_columns:
                if col in llm_responses_table.columns:
                    logger.error(f"❌ Deprecated column '{col}' still exists in database!")
                else:
                    logger.info(f"✅ Deprecated column '{col}' has been removed")
        
        # Force recreation of Base metadata
        Base.metadata.create_all(engine, checkfirst=True)
        
        logger.info("✅ Metadata cache cleared and refreshed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Error fixing metadata cache: {e}")
        return False

def test_llm_response_query():
    """Test if LlmResponse queries work without deprecated columns"""
    try:
        logger.info("🧪 Testing LlmResponse query...")
        
        from models import LlmResponse
        session = Session()
        
        # Try a simple count query
        count = session.query(LlmResponse).count()
        logger.info(f"✅ LlmResponse query successful: {count} records found")
        
        session.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ LlmResponse query failed: {e}")
        return False

if __name__ == "__main__":
    logger.info("🚀 Starting SQLAlchemy metadata fix...")
    
    # Fix metadata cache
    if fix_metadata_cache():
        # Test the fix
        if test_llm_response_query():
            logger.info("🎉 SQLAlchemy metadata fix completed successfully!")
        else:
            logger.error("❌ LlmResponse queries still failing after metadata fix")
    else:
        logger.error("❌ Failed to fix metadata cache")
