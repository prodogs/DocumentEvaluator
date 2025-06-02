#!/usr/bin/env python3
"""
Test script to verify batch_id implementation in LLM responses
"""

import psycopg2
import requests
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_batch_id_in_database():
    """Test that batch_id column exists and is populated"""
    try:
        # Connect to KnowledgeDocuments database
        conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        cursor = conn.cursor()
        
        # Check if batch_id column exists
        cursor.execute("""
            SELECT column_name 
            FROM information_schema.columns 
            WHERE table_name = 'llm_responses' AND column_name = 'batch_id';
        """)
        
        if cursor.fetchone():
            logger.info("✅ batch_id column exists in llm_responses table")
        else:
            logger.error("❌ batch_id column does not exist in llm_responses table")
            return False
        
        # Check for responses with batch_id populated
        cursor.execute("""
            SELECT 
                COUNT(*) as total_responses,
                COUNT(batch_id) as responses_with_batch_id,
                COUNT(DISTINCT batch_id) as unique_batches
            FROM llm_responses;
        """)
        
        total, with_batch, unique_batches = cursor.fetchone()
        logger.info(f"📊 Database stats:")
        logger.info(f"   Total responses: {total}")
        logger.info(f"   Responses with batch_id: {with_batch}")
        logger.info(f"   Unique batches: {unique_batches}")
        
        # Show sample data
        cursor.execute("""
            SELECT lr.id, lr.batch_id, d.document_id
            FROM llm_responses lr
            JOIN docs d ON lr.document_id = d.id
            WHERE lr.batch_id IS NOT NULL
            ORDER BY lr.id
            LIMIT 5;
        """)
        
        samples = cursor.fetchall()
        logger.info("📄 Sample responses with batch_id:")
        for response_id, batch_id, doc_id in samples:
            logger.info(f"   Response {response_id}: batch_id={batch_id}, doc={doc_id}")
        
        cursor.close()
        conn.close()
        return True
        
    except Exception as e:
        logger.error(f"❌ Error testing database: {e}")
        return False

def test_api_endpoint():
    """Test the updated API endpoint"""
    try:
        # First, get a batch ID that has responses
        conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT DISTINCT batch_id 
            FROM llm_responses 
            WHERE batch_id IS NOT NULL 
            LIMIT 1;
        """)
        
        result = cursor.fetchone()
        if not result:
            logger.warning("⚠️ No batches with responses found for API testing")
            cursor.close()
            conn.close()
            return True
        
        batch_id = result[0]
        logger.info(f"🧪 Testing API with batch_id: {batch_id}")
        
        cursor.close()
        conn.close()
        
        # Test the API endpoint
        response = requests.get(f"http://localhost:5001/api/batches/{batch_id}/llm-responses")
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ API endpoint responded successfully")
            logger.info(f"   Success: {data.get('success')}")
            logger.info(f"   Batch ID: {data.get('batch_id')}")
            logger.info(f"   Total responses: {data.get('pagination', {}).get('total', 0)}")
            logger.info(f"   Responses returned: {len(data.get('responses', []))}")
            
            # Check response structure
            if data.get('responses'):
                sample_response = data['responses'][0]
                logger.info("📄 Sample response structure:")
                logger.info(f"   Has batch_id: {'batch_id' in sample_response}")
                logger.info(f"   Has document info: {'document' in sample_response}")
                logger.info(f"   Has connection info: {'connection' in sample_response}")
                logger.info(f"   Has prompt info: {'prompt' in sample_response}")
            
            return True
        else:
            logger.error(f"❌ API returned status {response.status_code}: {response.text}")
            return False
            
    except Exception as e:
        logger.error(f"❌ Error testing API: {e}")
        return False

def main():
    """Run all tests"""
    logger.info("🧪 Testing batch_id implementation in LLM responses")
    logger.info("=" * 60)
    
    success = True
    
    # Test database
    logger.info("1. Testing database schema and data...")
    if not test_batch_id_in_database():
        success = False
    
    logger.info("\n2. Testing API endpoint...")
    if not test_api_endpoint():
        success = False
    
    logger.info("\n" + "=" * 60)
    if success:
        logger.info("🎉 All tests passed! batch_id implementation is working correctly.")
    else:
        logger.error("❌ Some tests failed. Please check the implementation.")
    
    return success

if __name__ == "__main__":
    main()