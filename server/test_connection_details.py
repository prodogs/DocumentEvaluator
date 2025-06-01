#!/usr/bin/env python3
"""
Test script to verify connection details capture functionality.
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from database import Session
from models import LlmResponse, Connection
from utils.connection_utils import capture_connection_details, get_display_info_from_connection_details
import json


def test_connection_details_capture():
    """Test capturing connection details for existing connections."""
    session = Session()
    
    try:
        print("🧪 Testing Connection Details Capture")
        print("=" * 50)
        
        # Get a few connections to test with
        connections = session.query(Connection).limit(3).all()
        
        if not connections:
            print("❌ No connections found in database. Please create some connections first.")
            return
        
        print(f"✅ Found {len(connections)} connections to test with")
        
        for connection in connections:
            print(f"\n🔍 Testing connection: {connection.name} (ID: {connection.id})")
            
            # Test capturing connection details
            connection_details = capture_connection_details(session, connection.id)
            
            if connection_details:
                print("✅ Successfully captured connection details:")
                print(json.dumps(connection_details, indent=2))
                
                # Test extracting display info
                display_info = get_display_info_from_connection_details(connection_details)
                print(f"\n📋 Display info extracted:")
                print(f"   Connection Name: {display_info['connection_name']}")
                print(f"   Provider Type: {display_info['provider_type']}")
                print(f"   Model Name: {display_info['model_name']}")
                print(f"   LLM Name (legacy): {display_info['llm_name']}")
                
            else:
                print("❌ Failed to capture connection details")
        
        # Test with non-existent connection
        print(f"\n🔍 Testing with non-existent connection ID: 99999")
        connection_details = capture_connection_details(session, 99999)
        if connection_details is None:
            print("✅ Correctly returned None for non-existent connection")
        else:
            print("❌ Should have returned None for non-existent connection")
            
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


def test_existing_llm_responses():
    """Test how existing LLM responses will be handled."""
    session = Session()
    
    try:
        print("\n🧪 Testing Existing LLM Responses")
        print("=" * 50)
        
        # Get a few existing LLM responses
        responses = session.query(LlmResponse).limit(5).all()
        
        if not responses:
            print("❌ No LLM responses found in database.")
            return
        
        print(f"✅ Found {len(responses)} existing LLM responses")
        
        for response in responses:
            print(f"\n🔍 Response ID: {response.id}")
            print(f"   Connection ID: {response.connection_id}")
            print(f"   Connection Details: {response.connection_details}")
            
            if response.connection_details:
                print("✅ Response already has connection details stored")
                display_info = get_display_info_from_connection_details(response.connection_details)
                print(f"   Display Name: {display_info['connection_name']}")
                print(f"   Model: {display_info['model_name']}")
            else:
                print("⚠️  Response has no connection details (expected for existing records)")
                
                # Test capturing details for this connection
                if response.connection_id:
                    connection_details = capture_connection_details(session, response.connection_id)
                    if connection_details:
                        print("✅ Could capture connection details for this response")
                    else:
                        print("❌ Could not capture connection details (connection may be deleted)")
                        
    except Exception as e:
        print(f"❌ Error during testing: {e}")
        import traceback
        traceback.print_exc()
    finally:
        session.close()


if __name__ == "__main__":
    print("🚀 Starting Connection Details Tests")
    test_connection_details_capture()
    test_existing_llm_responses()
    print("\n✅ Testing completed!")
