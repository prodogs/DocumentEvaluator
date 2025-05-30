#!/usr/bin/env python3
"""
Test script to manually process a task and verify score extraction works
"""

import sys
import os
import json
import requests

# Add the server directory to the Python path
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import LlmResponse
from api.status_polling import StatusPollingService

def test_score_processing():
    """Test the score processing with a known task ID"""
    print("🧪 Testing Score Processing")
    print("=" * 50)
    
    # Use the task ID from our recent test
    task_id = "1febae1c-7907-40eb-a51b-5987aed618f6"
    
    print(f"📋 Testing with task ID: {task_id}")
    
    # Get the response from the service
    url = f"http://localhost:7001/analyze_status/{task_id}"
    
    try:
        response = requests.get(url, timeout=10)
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Got response data")
            
            # Check if scoring_result exists
            scoring_result = data.get('scoring_result', {})
            if scoring_result:
                overall_score = scoring_result.get('overall_score')
                confidence = scoring_result.get('confidence')
                print(f"🎯 Found scoring data:")
                print(f"   Overall Score: {overall_score}")
                print(f"   Confidence: {confidence}")
                
                # Test our processing logic
                print(f"\n🔧 Testing score extraction logic...")
                
                # Simulate what our status polling service should do
                polling_service = StatusPollingService()
                
                # Create a mock LLM response record
                session = Session()
                try:
                    # Check if we already have a record for this task
                    existing_response = session.query(LlmResponse).filter(
                        LlmResponse.task_id == task_id
                    ).first()
                    
                    if existing_response:
                        print(f"📋 Found existing LLM response record (ID: {existing_response.id})")
                        
                        # Test our _handle_completed_task method
                        print(f"🔄 Processing with updated logic...")
                        polling_service._handle_completed_task(session, existing_response, data)
                        session.commit()
                        
                        # Check the results
                        session.refresh(existing_response)
                        print(f"✅ Processing completed!")
                        print(f"   Overall Score: {existing_response.overall_score}")
                        print(f"   Response JSON contains scoring: {'scoring_result' in json.loads(existing_response.response_json)}")
                        
                        # Show the formatted response text
                        if existing_response.response_text:
                            print(f"\n📄 Formatted Response Text (first 500 chars):")
                            print(existing_response.response_text[:500] + "..." if len(existing_response.response_text) > 500 else existing_response.response_text)
                        
                    else:
                        print(f"⚠️  No existing LLM response record found for this task")
                        print(f"   This suggests the task wasn't submitted through our system")
                        
                        # Create a test record to verify our logic works
                        print(f"🧪 Creating test record to verify logic...")
                        test_response = LlmResponse(
                            task_id=task_id,
                            status='P',  # Processing
                            llm_name='test-llm',
                            document_id=1,  # Dummy
                            prompt_id=1,    # Dummy
                            llm_config_id=1 # Dummy
                        )
                        session.add(test_response)
                        session.flush()  # Get the ID
                        
                        # Process it
                        polling_service._handle_completed_task(session, test_response, data)
                        session.commit()
                        
                        print(f"✅ Test processing completed!")
                        print(f"   Overall Score: {test_response.overall_score}")
                        print(f"   Status: {test_response.status}")
                        
                        # Clean up test record
                        session.delete(test_response)
                        session.commit()
                        print(f"🧹 Cleaned up test record")
                        
                except Exception as e:
                    print(f"❌ Error during processing: {e}")
                    import traceback
                    traceback.print_exc()
                    session.rollback()
                finally:
                    session.close()
                    
            else:
                print(f"❌ No scoring_result found in response")
                print(f"Available keys: {list(data.keys())}")
                
        elif response.status_code == 404:
            print(f"⚠️  Task not found (404) - task may have been cleaned up")
        else:
            print(f"❌ Error: {response.status_code}")
            print(f"Response: {response.text}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def check_recent_scores():
    """Check if any recent responses have scores"""
    print(f"\n🔍 Checking Recent Responses for Scores")
    print("=" * 50)
    
    session = Session()
    try:
        # Get recent responses
        recent_responses = session.query(LlmResponse).filter(
            LlmResponse.overall_score.isnot(None)
        ).order_by(LlmResponse.id.desc()).limit(5).all()
        
        if recent_responses:
            print(f"📊 Found {len(recent_responses)} responses with scores:")
            for response in recent_responses:
                print(f"   ID {response.id}: Score {response.overall_score}, Task {response.task_id}")
        else:
            print(f"⚠️  No responses with scores found yet")
            
        # Check total responses
        total_responses = session.query(LlmResponse).count()
        print(f"📈 Total responses in database: {total_responses}")
        
    except Exception as e:
        print(f"❌ Error checking scores: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    print("🧪 Score Processing Test")
    print("=" * 60)
    
    test_score_processing()
    check_recent_scores()
    
    print("\n" + "=" * 60)
    print("✅ Score processing test completed")
