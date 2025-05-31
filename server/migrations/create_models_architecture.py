#!/usr/bin/env python3
"""
Migration: Create Models Architecture

This migration creates the new Models architecture where:
1. Models are independent entities with standardized names
2. Service Providers are linked to Models through relationships
3. Model name normalization handles different provider naming conventions
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import Session, engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_models_architecture():
    """Create the new Models architecture"""
    session = Session()
    
    try:
        # Create Models table
        logger.info("Creating models table...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                common_name TEXT UNIQUE NOT NULL,
                display_name TEXT NOT NULL,
                notes TEXT,
                model_family TEXT,
                parameter_count TEXT,
                context_length INTEGER,
                capabilities TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                updated_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )
        """))
        
        # Create Provider-Model relationships table
        logger.info("Creating provider_models table...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS provider_models (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                provider_id INTEGER NOT NULL,
                model_id INTEGER NOT NULL,
                provider_model_name TEXT NOT NULL,
                is_active BOOLEAN DEFAULT FALSE,
                is_available BOOLEAN DEFAULT TRUE,
                last_checked DATETIME DEFAULT CURRENT_TIMESTAMP,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provider_id) REFERENCES llm_providers (id) ON DELETE CASCADE,
                FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE CASCADE,
                UNIQUE(provider_id, model_id)
            )
        """))
        
        # Create Model aliases table for name normalization
        logger.info("Creating model_aliases table...")
        session.execute(text("""
            CREATE TABLE IF NOT EXISTS model_aliases (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_id INTEGER NOT NULL,
                alias_name TEXT NOT NULL,
                provider_pattern TEXT,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (model_id) REFERENCES models (id) ON DELETE CASCADE,
                UNIQUE(alias_name, provider_pattern)
            )
        """))
        
        # Migrate existing llm_models data to new structure
        logger.info("Migrating existing model data...")
        
        # Get existing models from llm_models table
        existing_models = session.execute(text("""
            SELECT DISTINCT model_name, provider_id, model_id as provider_model_id, is_active
            FROM llm_models
        """)).fetchall()
        
        model_mapping = {}  # Track common_name -> model_id mapping
        
        for model_row in existing_models:
            model_name = model_row[0]
            provider_id = model_row[1] 
            provider_model_id = model_row[2]
            is_active = model_row[3]
            
            # Normalize model name to common name
            common_name = normalize_model_name(model_name)
            
            # Check if model already exists
            if common_name not in model_mapping:
                # Create new model entry
                result = session.execute(text("""
                    INSERT INTO models (common_name, display_name, model_family)
                    VALUES (:common_name, :display_name, :family)
                """), {
                    'common_name': common_name,
                    'display_name': model_name,
                    'family': extract_model_family(common_name)
                })
                
                model_id = result.lastrowid
                model_mapping[common_name] = model_id
                
                # Create alias for the original name
                session.execute(text("""
                    INSERT INTO model_aliases (model_id, alias_name)
                    VALUES (:model_id, :alias_name)
                """), {
                    'model_id': model_id,
                    'alias_name': model_name
                })
            else:
                model_id = model_mapping[common_name]
            
            # Create provider-model relationship
            session.execute(text("""
                INSERT OR IGNORE INTO provider_models 
                (provider_id, model_id, provider_model_name, is_active)
                VALUES (:provider_id, :model_id, :provider_model_name, :is_active)
            """), {
                'provider_id': provider_id,
                'model_id': model_id,
                'provider_model_name': model_name,
                'is_active': is_active
            })
        
        session.commit()
        logger.info("Successfully created models architecture and migrated data")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating models architecture: {e}")
        session.rollback()
        return False
    finally:
        session.close()

def normalize_model_name(provider_model_name):
    """Normalize provider-specific model names to common names"""
    name = provider_model_name.lower().strip()
    
    # Remove common prefixes
    prefixes_to_remove = [
        'qwen/', 'microsoft/', 'meta-llama/', 'mistralai/', 'anthropic/',
        'openai/', 'google/', 'cohere/', 'huggingface/'
    ]
    
    for prefix in prefixes_to_remove:
        if name.startswith(prefix):
            name = name[len(prefix):]
            break
    
    # Normalize separators
    name = name.replace(':', '-').replace('_', '-')
    
    # Handle common variations
    name_mappings = {
        'gpt-4': 'gpt-4',
        'gpt-4-turbo': 'gpt-4-turbo', 
        'gpt-3.5-turbo': 'gpt-3.5-turbo',
        'claude-3-opus': 'claude-3-opus',
        'claude-3-sonnet': 'claude-3-sonnet',
        'claude-3-haiku': 'claude-3-haiku',
        'llama-2-7b': 'llama-2-7b',
        'llama-2-13b': 'llama-2-13b',
        'llama-2-70b': 'llama-2-70b',
        'mistral-7b': 'mistral-7b',
        'qwen2-7b': 'qwen2-7b',
        'qwen2-14b': 'qwen2-14b',
        'qwen2-72b': 'qwen2-72b'
    }
    
    return name_mappings.get(name, name)

def extract_model_family(common_name):
    """Extract model family from common name"""
    if 'gpt' in common_name:
        return 'GPT'
    elif 'claude' in common_name:
        return 'Claude'
    elif 'llama' in common_name:
        return 'LLaMA'
    elif 'mistral' in common_name:
        return 'Mistral'
    elif 'qwen' in common_name:
        return 'Qwen'
    elif 'gemini' in common_name:
        return 'Gemini'
    else:
        return 'Other'

if __name__ == "__main__":
    logger.info("Starting migration: Create Models Architecture")
    
    success = create_models_architecture()
    
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
        sys.exit(1)
