#!/usr/bin/env python3
"""
Migration: Create Connections Table

This migration creates the connections table and adds the connection_id column
to the llm_configurations table to support the new connection management system.

Connections represent specific instances of providers with actual connection details.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from sqlalchemy import text
from database import Session, engine
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def create_connections_table():
    """Create the connections table and update llm_configurations"""
    session = Session()
    
    try:
        # Check if connections table already exists
        result = session.execute(text("""
            SELECT name FROM sqlite_master 
            WHERE type='table' AND name='connections'
        """))
        
        if result.fetchone():
            logger.info("Connections table already exists")
            return True
        
        # Create connections table
        logger.info("Creating connections table...")
        session.execute(text("""
            CREATE TABLE connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL,
                description TEXT,
                provider_id INTEGER NOT NULL,
                base_url TEXT,
                api_key TEXT,
                port_no INTEGER,
                connection_config TEXT,
                is_active BOOLEAN DEFAULT TRUE NOT NULL,
                connection_status TEXT DEFAULT 'unknown' NOT NULL,
                last_tested TIMESTAMP,
                last_test_result TEXT,
                supports_model_discovery BOOLEAN DEFAULT TRUE NOT NULL,
                available_models TEXT,
                last_model_sync TIMESTAMP,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (provider_id) REFERENCES llm_providers(id)
            )
        """))
        
        # Check if connection_id column exists in llm_configurations
        result = session.execute(text("""
            SELECT COUNT(*) as count 
            FROM pragma_table_info('llm_configurations') 
            WHERE name = 'connection_id'
        """))
        
        if result.fetchone()[0] == 0:
            logger.info("Adding connection_id column to llm_configurations...")
            session.execute(text("""
                ALTER TABLE llm_configurations 
                ADD COLUMN connection_id INTEGER REFERENCES connections(id)
            """))
        
        # Create some default connections based on existing providers
        logger.info("Creating default connections...")
        
        # Get existing providers
        providers = session.execute(text("""
            SELECT id, name, provider_type, default_base_url, auth_type, notes
            FROM llm_providers
        """)).fetchall()
        
        for provider in providers:
            provider_id = provider[0]
            provider_name = provider[1]
            provider_type = provider[2]
            default_base_url = provider[3]
            auth_type = provider[4]
            provider_notes = provider[5]
            
            # Create a default connection for each provider
            connection_name = f"Default {provider_name}"
            connection_description = f"Default connection for {provider_name} ({provider_type})"
            
            # Set default configuration based on provider type
            if provider_type == 'ollama':
                base_url = default_base_url or "http://localhost:11434"
                api_key = None
                port_no = 11434
            elif provider_type == 'openai':
                base_url = default_base_url or "https://api.openai.com/v1"
                api_key = "your-api-key-here"
                port_no = 443
            elif provider_type == 'lmstudio':
                base_url = default_base_url or "http://localhost:1234/v1"
                api_key = None
                port_no = 1234
            elif provider_type == 'amazon':
                base_url = default_base_url or "https://bedrock-runtime.us-east-1.amazonaws.com"
                api_key = "your-aws-credentials"
                port_no = 443
            elif provider_type == 'grok':
                base_url = default_base_url or "https://api.x.ai/v1"
                api_key = "your-grok-api-key"
                port_no = 443
            else:
                base_url = default_base_url
                api_key = "your-api-key-here"
                port_no = None
            
            session.execute(text("""
                INSERT INTO connections (
                    name, description, provider_id, base_url, api_key, port_no,
                    is_active, connection_status, supports_model_discovery, notes
                ) VALUES (
                    :name, :description, :provider_id, :base_url, :api_key, :port_no,
                    TRUE, 'unknown', TRUE, :notes
                )
            """), {
                'name': connection_name,
                'description': connection_description,
                'provider_id': provider_id,
                'base_url': base_url,
                'api_key': api_key,
                'port_no': port_no,
                'notes': f"Auto-created default connection. {provider_notes or ''}"
            })
            
            logger.info(f"Created default connection: {connection_name}")
        
        # Migrate existing LLM configurations to use connections
        logger.info("Migrating existing LLM configurations to use connections...")
        
        # Get existing configurations that don't have a connection_id
        configs = session.execute(text("""
            SELECT id, llm_name, provider_id, base_url, api_key, port_no
            FROM llm_configurations
            WHERE connection_id IS NULL AND provider_id IS NOT NULL
        """)).fetchall()
        
        for config in configs:
            config_id = config[0]
            provider_id = config[2]
            
            # Find the default connection for this provider
            connection = session.execute(text("""
                SELECT id FROM connections 
                WHERE provider_id = :provider_id 
                AND name LIKE 'Default %'
                LIMIT 1
            """), {'provider_id': provider_id}).fetchone()
            
            if connection:
                connection_id = connection[0]
                session.execute(text("""
                    UPDATE llm_configurations 
                    SET connection_id = :connection_id
                    WHERE id = :config_id
                """), {
                    'connection_id': connection_id,
                    'config_id': config_id
                })
                
                logger.info(f"Linked configuration '{config[1]}' to connection {connection_id}")
        
        session.commit()
        logger.info("Successfully created connections table and migrated data")
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating connections table: {e}")
        session.rollback()
        return False
    finally:
        session.close()

if __name__ == "__main__":
    logger.info("Starting migration: Create Connections Table")
    
    success = create_connections_table()
    
    if success:
        logger.info("Migration completed successfully!")
    else:
        logger.error("Migration failed!")
        sys.exit(1)
