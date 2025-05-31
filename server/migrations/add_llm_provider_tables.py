#!/usr/bin/env python3
"""
Migration: Add LLM Provider Management Tables

This migration adds the new tables and columns needed for the LLM provider management system:
- llm_providers table
- llm_models table  
- Enhanced llm_configurations table with new columns

Run this script to upgrade your database schema.
"""

import sys
import os
import logging
from datetime import datetime

# Add the parent directory to the path so we can import from server
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from server.database import get_engine, Session
from sqlalchemy import text, inspect
import psycopg2

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

def check_table_exists(engine, table_name):
    """Check if a table exists in the database"""
    inspector = inspect(engine)
    return table_name in inspector.get_table_names()

def check_column_exists(engine, table_name, column_name):
    """Check if a column exists in a table"""
    inspector = inspect(engine)
    if not check_table_exists(engine, table_name):
        return False
    columns = [col['name'] for col in inspector.get_columns(table_name)]
    return column_name in columns

def run_migration():
    """Run the migration to add LLM provider management tables"""
    engine = get_engine()
    
    logger.info("Starting LLM Provider Management migration...")
    
    with engine.connect() as conn:
        # Start transaction
        trans = conn.begin()
        
        try:
            # 1. Create llm_providers table
            if not check_table_exists(engine, 'llm_providers'):
                logger.info("Creating llm_providers table...")
                conn.execute(text("""
                    CREATE TABLE llm_providers (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        name TEXT UNIQUE NOT NULL,
                        provider_type TEXT NOT NULL,
                        default_base_url TEXT,
                        supports_model_discovery INTEGER DEFAULT 1 NOT NULL,
                        auth_type TEXT DEFAULT 'api_key' NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                logger.info("✅ llm_providers table created")
            else:
                logger.info("⏭️  llm_providers table already exists")

            # 2. Create llm_models table
            if not check_table_exists(engine, 'llm_models'):
                logger.info("Creating llm_models table...")
                conn.execute(text("""
                    CREATE TABLE llm_models (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        provider_id INTEGER REFERENCES llm_providers(id) ON DELETE CASCADE,
                        model_name TEXT NOT NULL,
                        model_id TEXT NOT NULL,
                        is_active INTEGER DEFAULT 0 NOT NULL,
                        capabilities TEXT,
                        last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    )
                """))
                logger.info("✅ llm_models table created")
            else:
                logger.info("⏭️  llm_models table already exists")

            # 3. Add new columns to llm_configurations table
            new_columns = [
                ('provider_id', 'INTEGER'),
                ('available_models', 'TEXT'),  # Use TEXT instead of JSON for SQLite compatibility
                ('model_discovery_enabled', 'INTEGER DEFAULT 1'),  # Use INTEGER for BOOLEAN in SQLite
                ('last_model_sync', 'TIMESTAMP'),
                ('connection_status', "TEXT DEFAULT 'unknown'"),
                ('provider_config', 'TEXT'),  # Use TEXT instead of JSON for SQLite compatibility
                ('created_at', 'TIMESTAMP')
            ]

            for column_name, column_def in new_columns:
                if not check_column_exists(engine, 'llm_configurations', column_name):
                    logger.info(f"Adding column {column_name} to llm_configurations...")
                    if column_name == 'created_at':
                        # Handle created_at separately for SQLite
                        conn.execute(text(f"ALTER TABLE llm_configurations ADD COLUMN {column_name} {column_def}"))
                        # Update existing rows with current timestamp
                        conn.execute(text("UPDATE llm_configurations SET created_at = CURRENT_TIMESTAMP WHERE created_at IS NULL"))
                    else:
                        conn.execute(text(f"ALTER TABLE llm_configurations ADD COLUMN {column_name} {column_def}"))
                    logger.info(f"✅ Column {column_name} added")
                else:
                    logger.info(f"⏭️  Column {column_name} already exists")

            # 4. Insert default providers
            logger.info("Inserting default LLM providers...")
            default_providers = [
                ('Ollama', 'ollama', 'http://localhost:11434', True, 'none'),
                ('OpenAI', 'openai', 'https://api.openai.com/v1', False, 'api_key'),
                ('LM Studio', 'lmstudio', 'http://localhost:1234/v1', True, 'none'),
                ('Amazon Bedrock', 'amazon', 'https://bedrock-runtime.us-east-1.amazonaws.com', False, 'aws_credentials'),
                ('Grok', 'grok', 'https://api.x.ai/v1', False, 'api_key')
            ]
            
            for name, provider_type, default_url, supports_discovery, auth_type in default_providers:
                # Check if provider already exists
                result = conn.execute(text("SELECT id FROM llm_providers WHERE name = :name"), {"name": name})
                if not result.fetchone():
                    conn.execute(text("""
                        INSERT INTO llm_providers (name, provider_type, default_base_url, supports_model_discovery, auth_type)
                        VALUES (:name, :provider_type, :default_url, :supports_discovery, :auth_type)
                    """), {
                        "name": name,
                        "provider_type": provider_type,
                        "default_url": default_url,
                        "supports_discovery": supports_discovery,
                        "auth_type": auth_type
                    })
                    logger.info(f"✅ Added default provider: {name}")
                else:
                    logger.info(f"⏭️  Provider {name} already exists")

            # 5. Update existing llm_configurations to link with providers
            logger.info("Linking existing configurations with providers...")
            conn.execute(text("""
                UPDATE llm_configurations 
                SET provider_id = (
                    SELECT id FROM llm_providers 
                    WHERE llm_providers.provider_type = llm_configurations.provider_type
                    LIMIT 1
                )
                WHERE provider_id IS NULL AND provider_type IS NOT NULL
            """))
            logger.info("✅ Existing configurations linked with providers")

            # Commit transaction
            trans.commit()
            logger.info("🎉 Migration completed successfully!")
            
        except Exception as e:
            # Rollback on error
            trans.rollback()
            logger.error(f"❌ Migration failed: {e}")
            raise

def rollback_migration():
    """Rollback the migration (for development/testing)"""
    engine = get_engine()
    
    logger.info("Rolling back LLM Provider Management migration...")
    
    with engine.connect() as conn:
        trans = conn.begin()
        
        try:
            # Remove added columns from llm_configurations
            columns_to_remove = [
                'provider_id', 'available_models', 'model_discovery_enabled',
                'last_model_sync', 'connection_status', 'provider_config', 'created_at'
            ]
            
            for column in columns_to_remove:
                if check_column_exists(engine, 'llm_configurations', column):
                    conn.execute(text(f"ALTER TABLE llm_configurations DROP COLUMN {column}"))
                    logger.info(f"✅ Removed column {column}")
            
            # Drop tables
            if check_table_exists(engine, 'llm_models'):
                conn.execute(text("DROP TABLE llm_models"))
                logger.info("✅ Dropped llm_models table")
                
            if check_table_exists(engine, 'llm_providers'):
                conn.execute(text("DROP TABLE llm_providers"))
                logger.info("✅ Dropped llm_providers table")
            
            trans.commit()
            logger.info("🎉 Rollback completed successfully!")
            
        except Exception as e:
            trans.rollback()
            logger.error(f"❌ Rollback failed: {e}")
            raise

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='LLM Provider Management Migration')
    parser.add_argument('--rollback', action='store_true', help='Rollback the migration')
    args = parser.parse_args()
    
    if args.rollback:
        rollback_migration()
    else:
        run_migration()
