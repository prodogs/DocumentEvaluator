#!/usr/bin/env python3
"""
Diagnostic script to identify the "batch completed but no LLM responses" issue
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Session
from models import Batch, LlmResponse, Document, Connection
from sqlalchemy import func
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def diagnose_batch_issue():
    """Diagnose the batch completion vs LLM responses issue"""
    
    session = Session()
    
    try:
        print("🔍 DIAGNOSING BATCH COMPLETION ISSUE")
        print("=" * 50)
        
        # 1. Check all completed batches
        print("\n1. COMPLETED BATCHES:")
        completed_batches = session.query(Batch).filter(Batch.status == 'COMPLETED').order_by(Batch.id.desc()).all()
        
        if not completed_batches:
            print("   No completed batches found.")
            return
        
        problematic_batches = []
        
        for batch in completed_batches:
            print(f"\n   Batch #{batch.batch_number} (ID: {batch.id}) - '{batch.batch_name}'")
            print(f"   Status: {batch.status}")
            print(f"   Created: {batch.created_at}")
            print(f"   Completed: {batch.completed_at}")
            
            # Count documents
            doc_count = session.query(Document).filter(Document.batch_id == batch.id).count()
            print(f"   Documents: {doc_count}")
            
            # Count LLM responses
            llm_response_count = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch.id
            ).count()
            print(f"   LLM Responses: {llm_response_count}")
            
            # Check connection_id status
            responses_with_connection = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch.id,
                LlmResponse.connection_id.isnot(None)
            ).count()
            print(f"   Responses with connection_id: {responses_with_connection}")
            
            # Check response statuses
            status_counts = session.query(LlmResponse.status, func.count(LlmResponse.id)).join(Document).filter(
                Document.batch_id == batch.id
            ).group_by(LlmResponse.status).all()
            
            if status_counts:
                print(f"   Status breakdown: {dict(status_counts)}")
            else:
                print("   Status breakdown: No responses found")
            
            # Identify problematic batches
            if llm_response_count == 0:
                print("   ⚠️  ISSUE: Batch marked as COMPLETED but has no LLM responses!")
                problematic_batches.append(batch)
            elif responses_with_connection == 0:
                print("   ⚠️  ISSUE: LLM responses exist but none have connection_id!")
                problematic_batches.append(batch)
        
        # 2. Check connections table
        print("\n\n2. CONNECTIONS STATUS:")
        connection_count = session.query(Connection).count()
        print(f"   Total connections: {connection_count}")
        
        if connection_count > 0:
            connections = session.query(Connection).all()
            for conn in connections:
                print(f"   Connection ID {conn.id}: {conn.name}")
        
        # 3. Analyze problematic batches
        if problematic_batches:
            print(f"\n\n3. PROBLEMATIC BATCHES ANALYSIS ({len(problematic_batches)} found):")
            
            for batch in problematic_batches:
                print(f"\n   Analyzing Batch #{batch.batch_number} (ID: {batch.id}):")
                
                # Check if batch has config_snapshot
                if batch.config_snapshot:
                    print("   ✅ Has config_snapshot")
                    config = batch.config_snapshot
                    if 'connections' in config:
                        print(f"   Config connections: {len(config['connections'])}")
                    if 'prompts' in config:
                        print(f"   Config prompts: {len(config['prompts'])}")
                else:
                    print("   ❌ No config_snapshot")
                
                # Check documents in batch
                documents = session.query(Document).filter(Document.batch_id == batch.id).all()
                print(f"   Documents in batch: {len(documents)}")
                
                for doc in documents:
                    responses = session.query(LlmResponse).filter(LlmResponse.document_id == doc.id).all()
                    print(f"     Document {doc.id}: {len(responses)} responses")
                    
                    for resp in responses:
                        print(f"       Response {resp.id}: status={resp.status}, connection_id={resp.connection_id}")
        
        # 4. Recommendations
        print("\n\n4. RECOMMENDATIONS:")
        
        if not problematic_batches:
            print("   ✅ No issues found with completed batches!")
        else:
            print("   📋 Issues found. Possible solutions:")
            print("   1. Run the connection_id migration script if not already done")
            print("   2. Check if LLM responses were created during batch staging")
            print("   3. Verify that the batch completion logic is working correctly")
            print("   4. Consider re-staging problematic batches")
        
    except Exception as e:
        logger.error(f"Error during diagnosis: {e}", exc_info=True)
    finally:
        session.close()

if __name__ == "__main__":
    diagnose_batch_issue()
