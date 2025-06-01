#!/usr/bin/env python3
"""
Test the API endpoint that the frontend uses to get LLM responses
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Session
from models import Batch, LlmResponse, Document, Prompt, Connection
from sqlalchemy.orm import joinedload

def test_llm_responses_api(batch_id):
    """Test the same query that the API endpoint uses"""
    
    session = Session()
    
    try:
        print(f"🔍 TESTING LLM RESPONSES API FOR BATCH {batch_id}")
        print("=" * 50)
        
        # Verify batch exists (same as API)
        batch = session.query(Batch).filter_by(id=batch_id).first()
        if not batch:
            print(f"❌ Batch {batch_id} not found")
            return
        
        print(f"✅ Batch found: #{batch.batch_number} - '{batch.batch_name}'")
        print(f"   Status: {batch.status}")
        
        # Build the same query as the API endpoint (from batch_routes.py line 515-519)
        query = session.query(LlmResponse).options(
            joinedload(LlmResponse.document),
            joinedload(LlmResponse.prompt),
            joinedload(LlmResponse.connection)
        ).join(Document).filter(Document.batch_id == batch_id)
        
        # Get total count
        total_count = query.count()
        print(f"   Total LLM responses found: {total_count}")
        
        # Get the responses
        responses = query.order_by(LlmResponse.timestamp.desc()).limit(100).all()
        
        print(f"   Retrieved {len(responses)} responses")
        
        if responses:
            print("\n📋 RESPONSE DETAILS:")
            for i, response in enumerate(responses):
                print(f"   Response {i+1}:")
                print(f"     ID: {response.id}")
                print(f"     Status: {response.status}")
                print(f"     Document ID: {response.document_id}")
                print(f"     Prompt ID: {response.prompt_id}")
                print(f"     Connection ID: {response.connection_id}")
                print(f"     Has response text: {bool(response.response_text)}")
                print(f"     Error: {response.error_message}")
                
                # Check relationships
                if response.document:
                    print(f"     Document: {response.document.filename}")
                else:
                    print(f"     Document: ❌ Not found")
                
                if response.prompt:
                    print(f"     Prompt: {response.prompt.description}")
                else:
                    print(f"     Prompt: ❌ Not found")
                
                if response.connection:
                    print(f"     Connection: {response.connection.name}")
                else:
                    print(f"     Connection: ❌ Not found")
                
                print()
        else:
            print("\n❌ NO RESPONSES FOUND")
            
            # Debug: Check if there are responses without the join
            direct_responses = session.query(LlmResponse).filter(
                LlmResponse.document_id.in_(
                    session.query(Document.id).filter(Document.batch_id == batch_id)
                )
            ).all()
            
            print(f"   Direct query (without joins): {len(direct_responses)} responses")
            
            if direct_responses:
                print("   ⚠️  Responses exist but join query failed!")
                for resp in direct_responses:
                    print(f"     Response {resp.id}: doc_id={resp.document_id}, connection_id={resp.connection_id}")
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()

def find_all_batches():
    """Find all batches to help identify which one to test"""
    session = Session()
    
    try:
        print("🔍 ALL BATCHES:")
        batches = session.query(Batch).order_by(Batch.id.desc()).all()
        
        for batch in batches:
            print(f"   Batch #{batch.batch_number} (ID: {batch.id}) - '{batch.batch_name}' - Status: {batch.status}")
        
        return batches
    finally:
        session.close()

if __name__ == "__main__":
    # First, show all batches
    batches = find_all_batches()
    
    if batches:
        print("\n" + "=" * 50)
        # Test the most recent batch
        test_batch_id = batches[0].id
        test_llm_responses_api(test_batch_id)
    else:
        print("No batches found")
