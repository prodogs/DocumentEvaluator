#!/usr/bin/env python3
"""
Check the schema of the docs table in KnowledgeDocuments database
"""

import psycopg2
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_docs_schema():
    """Check the structure of the docs table"""
    try:
        conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        cursor = conn.cursor()
        
        # Get table structure
        cursor.execute("""
            SELECT column_name, data_type, is_nullable
            FROM information_schema.columns 
            WHERE table_name = 'docs' 
            ORDER BY ordinal_position;
        """)
        
        columns = cursor.fetchall()
        logger.info("📊 docs table schema:")
        for col_name, data_type, nullable in columns:
            logger.info(f"   {col_name}: {data_type} ({'NULL' if nullable == 'YES' else 'NOT NULL'})")
        
        # Show sample data
        cursor.execute("SELECT * FROM docs LIMIT 3;")
        rows = cursor.fetchall()
        
        if rows:
            logger.info("\n📄 Sample docs data:")
            for i, row in enumerate(rows):
                logger.info(f"   Row {i+1}: {row}")
        else:
            logger.info("\n📄 No docs found in table")
        
        cursor.close()
        conn.close()
        
    except Exception as e:
        logger.error(f"❌ Error checking schema: {e}")

if __name__ == "__main__":
    check_docs_schema()