#!/usr/bin/env python3
"""
Add batch_id column to llm_responses table in KnowledgeDocuments database
and populate existing records with batch_id extracted from document_id pattern.
"""

import psycopg2
import re
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def add_batch_id_column():
    """Add batch_id column to llm_responses table and populate it"""
    
    # Connect to KnowledgeDocuments database
    try:
        conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments", 
            user="postgres",
            password="prodogs03",
            port=5432
        )
        cursor = conn.cursor()
        
        logger.info("Connected to KnowledgeDocuments database")
        
        # Step 1: Add batch_id column if it doesn't exist
        logger.info("Adding batch_id column to llm_responses table...")
        cursor.execute("""
            ALTER TABLE llm_responses 
            ADD COLUMN IF NOT EXISTS batch_id INTEGER;
        """)
        
        # Step 2: Create index on batch_id for better query performance
        logger.info("Creating index on batch_id column...")
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_llm_responses_batch_id 
            ON llm_responses(batch_id);
        """)
        
        # Step 3: Get all llm_responses that don't have batch_id populated
        logger.info("Finding responses without batch_id...")
        cursor.execute("""
            SELECT lr.id, d.document_id 
            FROM llm_responses lr
            JOIN docs d ON lr.document_id = d.id
            WHERE lr.batch_id IS NULL;
        """)
        
        responses_to_update = cursor.fetchall()
        logger.info(f"Found {len(responses_to_update)} responses to update")
        
        # Step 4: Extract batch_id from document_id pattern and update
        updated_count = 0
        pattern = re.compile(r'batch_(\d+)_doc_\d+')
        
        for response_id, document_id in responses_to_update:
            match = pattern.match(document_id)
            if match:
                batch_id = int(match.group(1))
                cursor.execute("""
                    UPDATE llm_responses 
                    SET batch_id = %s 
                    WHERE id = %s;
                """, (batch_id, response_id))
                updated_count += 1
                
                if updated_count % 100 == 0:
                    logger.info(f"Updated {updated_count} responses...")
        
        # Commit all changes
        conn.commit()
        
        # Step 5: Verify the update
        cursor.execute("""
            SELECT 
                COUNT(*) as total_responses,
                COUNT(batch_id) as responses_with_batch_id,
                COUNT(*) - COUNT(batch_id) as responses_without_batch_id
            FROM llm_responses;
        """)
        
        total, with_batch, without_batch = cursor.fetchone()
        
        logger.info("Migration completed successfully!")
        logger.info(f"Total responses: {total}")
        logger.info(f"Responses with batch_id: {with_batch}")
        logger.info(f"Responses without batch_id: {without_batch}")
        logger.info(f"Updated {updated_count} responses")
        
        # Show some sample data
        logger.info("Sample responses with batch_id:")
        cursor.execute("""
            SELECT lr.id, lr.batch_id, d.document_id
            FROM llm_responses lr
            JOIN docs d ON lr.document_id = d.id
            WHERE lr.batch_id IS NOT NULL
            ORDER BY lr.id
            LIMIT 5;
        """)
        
        samples = cursor.fetchall()
        for response_id, batch_id, doc_id in samples:
            logger.info(f"  Response {response_id}: batch_id={batch_id}, document_id={doc_id}")
        
    except Exception as e:
        logger.error(f"Error during migration: {e}")
        if 'conn' in locals():
            conn.rollback()
        raise
    finally:
        if 'cursor' in locals():
            cursor.close()
        if 'conn' in locals():
            conn.close()

if __name__ == "__main__":
    add_batch_id_column()