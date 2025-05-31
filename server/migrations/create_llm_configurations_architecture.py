#!/usr/bin/env python3
"""
Migration: Create LLM Configurations Architecture

This migration updates the LLM Configurations to work with the new
three-entity architecture: Models, Service Providers, and LLM Configurations.

LLM Configurations represent user selections of a specific Model + Service Provider
combination for batch processing operations.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import Session, engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def update_llm_configurations_architecture():
    """Update LLM Configurations to use the new architecture"""
    session = Session()
    
    try:
        # Check if the new columns already exist
        result = session.execute(text("""
            SELECT COUNT(*) as count 
            FROM pragma_table_info('llm_configurations') 
            WHERE name IN ('model_id', 'provider_model_id')
        """))
        
        existing_columns = result.fetchone()[0]
        
        if existing_columns == 2:
            logger.info("LLM Configurations architecture already updated")
            return True
        
        # Add new columns to llm_configurations
        logger.info("Adding new columns to llm_configurations table...")
        
        # Add model_id column (references the Models table)
        session.execute(text("""
            ALTER TABLE llm_configurations 
            ADD COLUMN model_id INTEGER REFERENCES models(id)
        """))
        
        # Add provider_model_id column (references the ProviderModel relationship)
        session.execute(text("""
            ALTER TABLE llm_configurations 
            ADD COLUMN provider_model_id INTEGER REFERENCES provider_models(id)
        """))
        
        # Add is_active column for global model activation
        session.execute(text("""
            ALTER TABLE llm_configurations 
            ADD COLUMN is_active BOOLEAN DEFAULT TRUE
        """))
        
        # Add configuration_type column (batch, interactive, etc.)
        session.execute(text("""
            ALTER TABLE llm_configurations 
            ADD COLUMN configuration_type TEXT DEFAULT 'batch'
        """))
        
        # Add user_notes column for configuration-specific notes
        session.execute(text("""
            ALTER TABLE llm_configurations 
            ADD COLUMN user_notes TEXT
        """))
        
        # Migrate existing configurations to new structure
        logger.info("Migrating existing LLM configurations...")
        
        # Get existing configurations
        existing_configs = session.execute(text("""
            SELECT id, provider_id, model_name, llm_name, created_at
            FROM llm_configurations
            WHERE model_id IS NULL
        """)).fetchall()
        
        for config in existing_configs:
            config_id = config[0]
            provider_id = config[1]
            model_name = config[2]
            
            # Find the corresponding model and provider_model relationship
            provider_model = session.execute(text("""
                SELECT pm.id, pm.model_id
                FROM provider_models pm
                JOIN models m ON pm.model_id = m.id
                WHERE pm.provider_id = :provider_id 
                AND (pm.provider_model_name = :model_name OR m.common_name = :model_name)
                LIMIT 1
            """), {
                'provider_id': provider_id,
                'model_name': model_name
            }).fetchone()
            
            if provider_model:
                provider_model_id = provider_model[0]
                model_id = provider_model[1]
                
                # Update the configuration with new relationships
                session.execute(text("""
                    UPDATE llm_configurations 
                    SET model_id = :model_id, 
                        provider_model_id = :provider_model_id,
                        is_active = TRUE,
                        configuration_type = 'batch'
                    WHERE id = :config_id
                """), {
                    'model_id': model_id,
                    'provider_model_id': provider_model_id,
                    'config_id': config_id
                })
                
                logger.info(f"Migrated configuration '{config[3]}' to new architecture")
            else:
                logger.warning(f"Could not find model '{model_name}' for provider {provider_id} in configuration '{config[3]}'")
        
        # Add global model activation status
        logger.info("Adding global activation status to models...")
        
        # Check if is_globally_active column exists in models table
        result = session.execute(text("""
            SELECT COUNT(*) as count 
            FROM pragma_table_info('models') 
            WHERE name = 'is_globally_active'
        """))
        
        if result.fetchone()[0] == 0:
            session.execute(text("""
                ALTER TABLE models 
                ADD COLUMN is_globally_active BOOLEAN DEFAULT TRUE
            """))
        
        session.commit()
        logger.info("Successfully updated LLM Configurations architecture")
        
        return True
        
    except Exception as e:
        logger.error(f"Error updating LLM Configurations architecture: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("Starting migration: Update LLM Configurations Architecture")
    
    success = update_llm_configurations_architecture()
    
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
        sys.exit(1)
