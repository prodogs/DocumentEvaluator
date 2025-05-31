#!/usr/bin/env python3
"""
Migration: Add connection_id to llm_responses table and migrate from llm_configurations

This migration:
1. Adds connection_id column to llm_responses table
2. Migrates existing llm_responses to use connections instead of llm_configurations
3. Makes connection_id required (NOT NULL)
4. Adds foreign key constraint to connections table

Run this migration to update the schema from the deprecated llm_configurations 
system to the new connections system.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_db_connection
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def run_migration():
    """Run the migration to add connection_id to llm_responses"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("🚀 Starting migration: Add connection_id to llm_responses")
        
        # Step 1: Check if connection_id column already exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'llm_responses' AND column_name = 'connection_id'
        """)
        
        if cursor.fetchone():
            logger.info("✅ connection_id column already exists in llm_responses table")
            return
        
        # Step 2: Add connection_id column (nullable initially)
        logger.info("📝 Adding connection_id column to llm_responses table...")
        cursor.execute("""
            ALTER TABLE llm_responses 
            ADD COLUMN connection_id INTEGER
        """)
        
        # Step 3: Find the first active connection to use as default
        logger.info("🔍 Finding default connection for migration...")
        cursor.execute("""
            SELECT id FROM connections 
            WHERE is_active = true 
            ORDER BY id 
            LIMIT 1
        """)
        
        default_connection = cursor.fetchone()
        if not default_connection:
            logger.warning("⚠️  No active connections found. Creating a placeholder...")
            # Create a placeholder connection for migration
            cursor.execute("""
                INSERT INTO connections (
                    name, provider_type, base_url, is_active, 
                    connection_status, created_at
                ) VALUES (
                    'Migration Placeholder', 'openai', 'https://api.openai.com/v1', 
                    false, 'not_tested', NOW()
                ) RETURNING id
            """)
            default_connection = cursor.fetchone()
        
        default_connection_id = default_connection[0]
        logger.info(f"📌 Using connection ID {default_connection_id} as default")
        
        # Step 4: Update existing llm_responses to use the default connection
        logger.info("🔄 Migrating existing llm_responses to use connections...")
        cursor.execute("""
            UPDATE llm_responses 
            SET connection_id = %s 
            WHERE connection_id IS NULL
        """, (default_connection_id,))
        
        rows_updated = cursor.rowcount
        logger.info(f"✅ Updated {rows_updated} llm_responses records")
        
        # Step 5: Make connection_id NOT NULL
        logger.info("🔒 Making connection_id column NOT NULL...")
        cursor.execute("""
            ALTER TABLE llm_responses 
            ALTER COLUMN connection_id SET NOT NULL
        """)
        
        # Step 6: Add foreign key constraint
        logger.info("🔗 Adding foreign key constraint...")
        cursor.execute("""
            ALTER TABLE llm_responses 
            ADD CONSTRAINT fk_llm_responses_connection 
            FOREIGN KEY (connection_id) REFERENCES connections(id) 
            ON DELETE CASCADE
        """)
        
        # Step 7: Create index for performance
        logger.info("📊 Creating index on connection_id...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_responses_connection_id 
            ON llm_responses(connection_id)
        """)
        
        # Commit all changes
        conn.commit()
        logger.info("✅ Migration completed successfully!")
        
        # Step 8: Show summary
        cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE connection_id IS NOT NULL")
        total_responses = cursor.fetchone()[0]
        
        cursor.execute("SELECT COUNT(*) FROM connections WHERE is_active = true")
        active_connections = cursor.fetchone()[0]
        
        logger.info(f"📊 Migration Summary:")
        logger.info(f"   - {total_responses} llm_responses now use connections")
        logger.info(f"   - {active_connections} active connections available")
        logger.info(f"   - Foreign key constraint added")
        logger.info(f"   - Index created for performance")
        
    except Exception as e:
        logger.error(f"❌ Migration failed: {str(e)}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

def rollback_migration():
    """Rollback the migration (remove connection_id column)"""
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        logger.info("🔄 Rolling back migration: Remove connection_id from llm_responses")
        
        # Drop foreign key constraint
        cursor.execute("""
            ALTER TABLE llm_responses 
            DROP CONSTRAINT IF EXISTS fk_llm_responses_connection
        """)
        
        # Drop index
        cursor.execute("""
            DROP INDEX IF EXISTS idx_llm_responses_connection_id
        """)
        
        # Drop column
        cursor.execute("""
            ALTER TABLE llm_responses 
            DROP COLUMN IF EXISTS connection_id
        """)
        
        conn.commit()
        logger.info("✅ Migration rollback completed successfully!")
        
    except Exception as e:
        logger.error(f"❌ Rollback failed: {str(e)}")
        conn.rollback()
        raise
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    if len(sys.argv) > 1 and sys.argv[1] == "rollback":
        rollback_migration()
    else:
        run_migration()
