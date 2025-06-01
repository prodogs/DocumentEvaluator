#!/usr/bin/env python3
"""
Test the connection details implementation without starting the full server.
"""

import os
import sys
import json
from datetime import datetime

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def test_connection_details_implementation():
    """Test our connection details implementation."""
    print("🧪 Testing Connection Details Implementation")
    print("=" * 60)
    
    try:
        # Test 1: Import our utility functions
        print("📦 Testing imports...")
        from utils.connection_utils import (
            capture_connection_details, 
            get_display_info_from_connection_details,
            format_connection_for_api_response
        )
        print("✅ Utility functions imported successfully")
        
        # Test 2: Test with mock data (simulating what would be captured)
        print("\n🔍 Testing with mock connection details...")
        mock_connection_details = {
            "connection": {
                "id": 1,
                "name": "Test Ollama Connection",
                "description": "Test connection for Ollama",
                "base_url": "http://localhost:11434",
                "port_no": 11434,
                "is_active": True,
                "connection_status": "active",
                "created_at": "2025-05-31T23:00:00"
            },
            "provider": {
                "id": 1,
                "provider_type": "ollama",
                "provider_name": "Ollama"
            },
            "model": {
                "id": 1,
                "display_name": "Llama 3.1 8B",
                "model_identifier": "llama3.1:8b"
            },
            "captured_at": datetime.now().isoformat(),
            "version": "1.0"
        }
        
        print("✅ Mock connection details created:")
        print(json.dumps(mock_connection_details, indent=2))
        
        # Test 3: Test display info extraction
        print("\n📋 Testing display info extraction...")
        display_info = get_display_info_from_connection_details(mock_connection_details)
        print("✅ Display info extracted:")
        for key, value in display_info.items():
            print(f"   {key}: {value}")
        
        # Test 4: Test API response formatting
        print("\n🌐 Testing API response formatting...")
        api_response = format_connection_for_api_response(mock_connection_details)
        print("✅ API response formatted:")
        print(json.dumps(api_response, indent=2))
        
        # Test 5: Test with None (fallback scenario)
        print("\n⚠️  Testing fallback scenario (no connection details)...")
        fallback_display = get_display_info_from_connection_details(None)
        print("✅ Fallback display info:")
        for key, value in fallback_display.items():
            print(f"   {key}: {value}")
        
        fallback_api = format_connection_for_api_response(None)
        print("✅ Fallback API response:", fallback_api)
        
        print("\n🎉 All tests passed! Implementation is working correctly.")
        return True
        
    except Exception as e:
        print(f"❌ Test failed with error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_database_schema():
    """Test that our new database column exists."""
    print("\n🗄️  Testing Database Schema")
    print("=" * 60)
    
    try:
        from database import Session
        from models import LlmResponse
        from sqlalchemy import inspect
        
        # Create a session
        session = Session()
        
        # Get table info
        inspector = inspect(session.bind)
        columns = inspector.get_columns('llm_responses')
        
        # Check if our new column exists
        column_names = [col['name'] for col in columns]
        
        if 'connection_details' in column_names:
            print("✅ connection_details column exists in llm_responses table")
            
            # Get column info
            connection_details_col = next(col for col in columns if col['name'] == 'connection_details')
            print(f"   Column type: {connection_details_col['type']}")
            print(f"   Nullable: {connection_details_col['nullable']}")
            
        else:
            print("❌ connection_details column NOT found in llm_responses table")
            print("Available columns:", column_names)
            
        session.close()
        return 'connection_details' in column_names
        
    except Exception as e:
        print(f"❌ Database schema test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_model_changes():
    """Test that our model changes are working."""
    print("\n🏗️  Testing Model Changes")
    print("=" * 60)
    
    try:
        from models import LlmResponse
        from sqlalchemy.dialects.postgresql import JSONB
        
        # Check if the model has the new attribute
        if hasattr(LlmResponse, 'connection_details'):
            print("✅ LlmResponse model has connection_details attribute")
            
            # Check the column type
            column = LlmResponse.__table__.columns.get('connection_details')
            if column is not None:
                print(f"   Column type: {type(column.type)}")
                print(f"   Nullable: {column.nullable}")
                
                # Check if it's JSONB type
                if isinstance(column.type, JSONB):
                    print("✅ Column is correctly defined as JSONB")
                else:
                    print(f"⚠️  Column type is {type(column.type)}, expected JSONB")
            else:
                print("❌ connection_details column not found in model")
                
        else:
            print("❌ LlmResponse model does NOT have connection_details attribute")
            
        return hasattr(LlmResponse, 'connection_details')
        
    except Exception as e:
        print(f"❌ Model test failed: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("🚀 Starting Implementation Tests")
    print("=" * 60)
    
    # Run all tests
    test1_passed = test_connection_details_implementation()
    test2_passed = test_database_schema()
    test3_passed = test_model_changes()
    
    print("\n📊 Test Results Summary")
    print("=" * 60)
    print(f"✅ Utility Functions Test: {'PASSED' if test1_passed else 'FAILED'}")
    print(f"✅ Database Schema Test: {'PASSED' if test2_passed else 'FAILED'}")
    print(f"✅ Model Changes Test: {'PASSED' if test3_passed else 'FAILED'}")
    
    if all([test1_passed, test2_passed, test3_passed]):
        print("\n🎉 ALL TESTS PASSED! Implementation is ready.")
    else:
        print("\n⚠️  Some tests failed. Please review the implementation.")
