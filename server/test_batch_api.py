#!/usr/bin/env python3
"""
Test the batch API endpoint directly
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Session
from models import Batch, LlmResponse, Document, Prompt, Connection
from sqlalchemy.orm import joinedload

def test_batch_api_query(batch_id):
    """Test the exact query used by the API"""
    
    session = Session()
    
    try:
        print(f"🧪 TESTING API QUERY FOR BATCH {batch_id}")
        print("=" * 50)
        
        # This is the exact query from batch_routes.py line 515-519
        query = session.query(LlmResponse).options(
            joinedload(LlmResponse.document),
            joinedload(LlmResponse.prompt),
            joinedload(LlmResponse.connection)
        ).join(Document).filter(Document.batch_id == batch_id)
        
        # Get count
        total_count = query.count()
        print(f"Query result count: {total_count}")
        
        # Get responses
        responses = query.order_by(LlmResponse.timestamp.desc()).limit(100).all()
        print(f"Retrieved responses: {len(responses)}")
        
        if responses:
            print("\n📋 RESPONSE DETAILS:")
            for i, response in enumerate(responses):
                print(f"Response {i+1}:")
                print(f"  ID: {response.id}")
                print(f"  Status: {response.status}")
                print(f"  Document: {response.document.filename if response.document else 'None'}")
                print(f"  Prompt: {response.prompt.description if response.prompt else 'None'}")
                print(f"  Connection: {response.connection.name if response.connection else 'None'}")
                print(f"  Has text: {bool(response.response_text)}")
                print()
        else:
            print("❌ No responses found")
            
            # Debug: Check what's in the database
            print("\n🔍 DEBUG INFO:")
            
            # Check if batch exists
            batch = session.query(Batch).filter_by(id=batch_id).first()
            if batch:
                print(f"✅ Batch exists: #{batch.batch_number} - {batch.batch_name}")
            else:
                print(f"❌ Batch {batch_id} not found")
                return
            
            # Check documents
            documents = session.query(Document).filter(Document.batch_id == batch_id).all()
            print(f"Documents in batch: {len(documents)}")
            
            for doc in documents:
                print(f"  Document {doc.id}: {doc.filename}")
                
                # Check responses for this document
                doc_responses = session.query(LlmResponse).filter(LlmResponse.document_id == doc.id).all()
                print(f"    Responses: {len(doc_responses)}")
                
                for resp in doc_responses:
                    print(f"      Response {resp.id}: status={resp.status}, connection_id={resp.connection_id}")
                    
                    # Check if relationships exist
                    if resp.connection_id:
                        connection = session.query(Connection).filter_by(id=resp.connection_id).first()
                        print(f"        Connection: {connection.name if connection else 'NOT FOUND'}")
                    
                    if resp.prompt_id:
                        prompt = session.query(Prompt).filter_by(id=resp.prompt_id).first()
                        print(f"        Prompt: {prompt.description if prompt else 'NOT FOUND'}")
        
        return total_count > 0
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False
    finally:
        session.close()

def main():
    """Main function"""
    
    session = Session()
    
    try:
        # Get the most recent batch
        batch = session.query(Batch).order_by(Batch.id.desc()).first()
        
        if not batch:
            print("No batches found")
            return
        
        print(f"Testing with Batch #{batch.batch_number} (ID: {batch.id})")
        test_batch_api_query(batch.id)
        
    finally:
        session.close()

if __name__ == "__main__":
    main()
