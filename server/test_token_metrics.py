#!/usr/bin/env python3
"""
Test script to verify token metrics extraction and persistence functionality.

This script tests:
1. Token metrics extraction from analyze_status response format
2. Database persistence of token metrics
3. Compatibility with the OpenAPI specification
"""

import sys
import os
import json

# Add the server directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from api.status_polling import StatusPollingService

def test_token_metrics_extraction():
    """Test the _extract_token_metrics method with sample data"""
    print("Testing token metrics extraction...")
    
    # Create a StatusPollingService instance to access the method
    polling_service = StatusPollingService()
    
    # Sample analyze_status response results (matching OpenAPI spec)
    sample_results = [
        {
            "prompt": "Summarize this document",
            "response": "This document covers REST API development best practices...",
            "status": "success",
            "error_message": None,
            "input_tokens": 150,
            "output_tokens": 75,
            "time_taken_seconds": 3.2,
            "tokens_per_second": 23.44
        },
        {
            "prompt": "Extract key points",
            "response": "Key points: 1. API design, 2. Error handling, 3. Authentication...",
            "status": "success", 
            "error_message": None,
            "input_tokens": 120,
            "output_tokens": 45,
            "time_taken_seconds": 2.1,
            "tokens_per_second": 21.43
        }
    ]
    
    # Test extraction
    metrics = polling_service._extract_token_metrics(sample_results)
    
    print("Extracted metrics:")
    print(json.dumps(metrics, indent=2))
    
    # Verify expected values
    expected_input_tokens = 150 + 120  # 270
    expected_output_tokens = 75 + 45   # 120
    expected_time_taken = 3.2 + 2.1    # 5.3
    expected_tokens_per_second = 120 / 5.3  # ~22.64
    
    assert metrics['input_tokens'] == expected_input_tokens, f"Expected {expected_input_tokens}, got {metrics['input_tokens']}"
    assert metrics['output_tokens'] == expected_output_tokens, f"Expected {expected_output_tokens}, got {metrics['output_tokens']}"
    assert abs(metrics['time_taken_seconds'] - expected_time_taken) < 0.01, f"Expected {expected_time_taken}, got {metrics['time_taken_seconds']}"
    assert abs(metrics['tokens_per_second'] - expected_tokens_per_second) < 0.1, f"Expected ~{expected_tokens_per_second:.2f}, got {metrics['tokens_per_second']}"
    
    print("✅ Token metrics extraction test passed!")
    return True

def test_empty_results():
    """Test extraction with empty or invalid results"""
    print("\nTesting empty/invalid results...")
    
    polling_service = StatusPollingService()
    
    # Test empty results
    metrics = polling_service._extract_token_metrics([])
    assert metrics == {}, f"Expected empty dict, got {metrics}"
    
    # Test None results
    metrics = polling_service._extract_token_metrics(None)
    assert metrics == {}, f"Expected empty dict, got {metrics}"
    
    # Test results without token info
    results_without_tokens = [
        {
            "prompt": "Test prompt",
            "response": "Test response",
            "status": "success"
        }
    ]
    metrics = polling_service._extract_token_metrics(results_without_tokens)
    assert metrics == {}, f"Expected empty dict, got {metrics}"
    
    print("✅ Empty/invalid results test passed!")
    return True

def test_partial_token_data():
    """Test extraction with partial token data"""
    print("\nTesting partial token data...")
    
    polling_service = StatusPollingService()
    
    # Results with only some token fields
    partial_results = [
        {
            "prompt": "Test prompt 1",
            "response": "Test response 1",
            "status": "success",
            "input_tokens": 100,
            # Missing output_tokens, time_taken_seconds, tokens_per_second
        },
        {
            "prompt": "Test prompt 2", 
            "response": "Test response 2",
            "status": "success",
            "output_tokens": 50,
            "time_taken_seconds": 2.0
            # Missing input_tokens, tokens_per_second will be calculated
        }
    ]
    
    metrics = polling_service._extract_token_metrics(partial_results)
    
    print("Partial metrics:")
    print(json.dumps(metrics, indent=2))
    
    # Should aggregate available data
    assert metrics['input_tokens'] == 100, f"Expected 100, got {metrics['input_tokens']}"
    assert metrics['output_tokens'] == 50, f"Expected 50, got {metrics['output_tokens']}"
    assert metrics['time_taken_seconds'] == 2.0, f"Expected 2.0, got {metrics['time_taken_seconds']}"
    assert metrics['tokens_per_second'] == 25.0, f"Expected 25.0, got {metrics['tokens_per_second']}"  # 50/2.0
    
    print("✅ Partial token data test passed!")
    return True

def test_database_schema():
    """Test that the database schema includes the new token fields"""
    print("\nTesting database schema...")
    
    from database import Session
    from sqlalchemy import text
    
    session = Session()
    try:
        # Check if the new columns exist
        result = session.execute(text("PRAGMA table_info(llm_responses)"))
        columns = result.fetchall()
        
        column_names = [col[1] for col in columns]
        
        required_columns = ['input_tokens', 'output_tokens', 'time_taken_seconds', 'tokens_per_second']
        
        for col in required_columns:
            assert col in column_names, f"Column {col} not found in llm_responses table"
        
        print(f"✅ All required token metric columns found: {required_columns}")
        
        # Show the full schema
        print("\nCurrent llm_responses table schema:")
        for col in columns:
            print(f"  {col[1]} {col[2]} {'NOT NULL' if col[3] else 'NULL'}")
            
    finally:
        session.close()
    
    return True

def main():
    """Run all tests"""
    print("🧪 Testing Token Metrics Implementation")
    print("=" * 50)
    
    try:
        # Run all tests
        test_token_metrics_extraction()
        test_empty_results()
        test_partial_token_data()
        test_database_schema()
        
        print("\n" + "=" * 50)
        print("🎉 All tests passed! Token metrics implementation is working correctly.")
        print("\n📋 Summary:")
        print("✅ Token metrics extraction from analyze_status response")
        print("✅ Database schema includes token metric columns")
        print("✅ Proper handling of empty/partial data")
        print("✅ Aggregation of metrics across multiple prompts")
        
        return True
        
    except Exception as e:
        print(f"\n❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
