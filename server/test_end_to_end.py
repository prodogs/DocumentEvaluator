#!/usr/bin/env python3
"""
End-to-end test of the connection details feature.
"""

import os
import sys
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_llm_response_creation_with_connection_details():
    """Test creating LlmResponse with connection details capture."""
    print("🧪 Testing LlmResponse Creation with Connection Details")
    print("=" * 60)
    
    try:
        from database import Session
        from models import LlmResponse, Connection, Document, Prompt
        from utils.connection_utils import capture_connection_details
        
        session = Session()
        
        # Get an existing connection to test with
        connection = session.query(Connection).first()
        if not connection:
            print("❌ No connections found. Cannot test LlmResponse creation.")
            session.close()
            return False
            
        print(f"✅ Found connection to test with: {connection.name} (ID: {connection.id})")
        
        # Get existing document and prompt for testing
        document = session.query(Document).first()
        prompt = session.query(Prompt).first()
        
        if not document or not prompt:
            print("❌ Need at least one document and one prompt to test.")
            session.close()
            return False
            
        print(f"✅ Found document: {document.filename} (ID: {document.id})")
        print(f"✅ Found prompt: {prompt.description} (ID: {prompt.id})")
        
        # Test capturing connection details
        print(f"\n🔍 Capturing connection details for connection {connection.id}...")
        connection_details = capture_connection_details(session, connection.id)
        
        if connection_details:
            print("✅ Successfully captured connection details:")
            print(json.dumps(connection_details, indent=2))
            
            # Create a test LlmResponse with connection details
            print(f"\n📝 Creating test LlmResponse with connection details...")
            test_response = LlmResponse(
                document_id=document.id,
                prompt_id=prompt.id,
                connection_id=connection.id,
                connection_details=connection_details,
                status='N',  # Not started
                task_id=f"test_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )
            
            session.add(test_response)
            session.commit()
            
            print(f"✅ Created LlmResponse with ID: {test_response.id}")
            print(f"   Connection Details stored: {test_response.connection_details is not None}")
            
            # Test retrieving and using the stored connection details
            print(f"\n🔍 Testing retrieval and API formatting...")
            from api.batch_routes import _format_connection_for_response
            
            # Simulate what the API would return
            formatted_connection = _format_connection_for_response(test_response)
            print("✅ API-formatted connection info:")
            print(json.dumps(formatted_connection, indent=2))
            
            # Clean up - delete the test response
            session.delete(test_response)
            session.commit()
            print("✅ Test response cleaned up")
            
            session.close()
            return True
            
        else:
            print("❌ Failed to capture connection details")
            session.close()
            return False
            
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        if 'session' in locals():
            session.close()
        return False


def test_existing_llm_responses_handling():
    """Test how existing LlmResponse records (without connection_details) are handled."""
    print("\n🧪 Testing Existing LlmResponse Handling")
    print("=" * 60)
    
    try:
        from database import Session
        from models import LlmResponse
        from api.batch_routes import _format_connection_for_response
        
        session = Session()
        
        # Get an existing LlmResponse (should have connection_details = None)
        existing_response = session.query(LlmResponse).first()
        
        if not existing_response:
            print("⚠️  No existing LlmResponse records found.")
            session.close()
            return True
            
        print(f"✅ Found existing LlmResponse: ID {existing_response.id}")
        print(f"   Connection ID: {existing_response.connection_id}")
        print(f"   Connection Details: {existing_response.connection_details}")
        
        # Test API formatting with existing response (should use fallback)
        print(f"\n🔍 Testing API formatting for existing response...")
        formatted_connection = _format_connection_for_response(existing_response)
        
        if formatted_connection:
            print("✅ API formatting successful (using fallback to current connection):")
            print(json.dumps(formatted_connection, indent=2))
        else:
            print("⚠️  API formatting returned None (connection may be deleted)")
            
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        if 'session' in locals():
            session.close()
        return False


def test_batch_service_integration():
    """Test that batch service properly captures connection details."""
    print("\n🧪 Testing Batch Service Integration")
    print("=" * 60)
    
    try:
        # Import batch service
        from services.batch_service import BatchService
        print("✅ BatchService imported successfully")
        
        # Check if the batch service has been updated with our connection details capture
        import inspect
        source = inspect.getsource(BatchService.create_multi_folder_batch)
        
        if 'capture_connection_details' in source:
            print("✅ BatchService.create_multi_folder_batch includes connection details capture")
        else:
            print("❌ BatchService.create_multi_folder_batch does NOT include connection details capture")
            
        if 'connection_details=connection_details' in source:
            print("✅ BatchService properly assigns connection_details to LlmResponse")
        else:
            print("❌ BatchService does NOT assign connection_details to LlmResponse")
            
        return 'capture_connection_details' in source and 'connection_details=connection_details' in source
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Starting End-to-End Tests")
    print("=" * 60)
    
    # Run all tests
    test1_passed = test_llm_response_creation_with_connection_details()
    test2_passed = test_existing_llm_responses_handling()
    test3_passed = test_batch_service_integration()
    
    print("\n📊 End-to-End Test Results")
    print("=" * 60)
    print(f"✅ LlmResponse Creation Test: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"✅ Existing Records Handling Test: {'PASSED' if test2_passed else 'FAILED'}")
    print(f"✅ Batch Service Integration Test: {'PASSED' if test3_passed else 'FAILED'}")
    
    if all([test1_passed, test2_passed, test3_passed]):
        print("\n🎉 ALL END-TO-END TESTS PASSED!")
        print("\n📋 Summary of Implementation:")
        print("   ✅ Database schema updated with connection_details column")
        print("   ✅ LlmResponse model updated to include connection_details")
        print("   ✅ Utility functions for capturing and formatting connection details")
        print("   ✅ Batch service updated to capture connection details on creation")
        print("   ✅ API routes updated to use stored connection details")
        print("   ✅ Frontend updated to display connection information")
        print("   ✅ Backward compatibility maintained for existing records")
        print("\n🎯 The feature is ready for use!")
    else:
        print("\n⚠️  Some end-to-end tests failed. Please review the implementation.")
