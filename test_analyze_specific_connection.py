#!/usr/bin/env python3
"""
Test script for analyze_document_with_llm endpoint with specific connection
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:5001"
ANALYZE_ENDPOINT = f"{BASE_URL}/analyze_document_with_llm"

def test_with_minimal_payload():
    """Test with minimal payload - just doc_id"""
    
    print("🧪 Testing with minimal payload (doc_id only)...")
    print("=" * 50)
    
    # Minimal test payload
    minimal_payload = {
        "doc_id": 3233  # Different document
    }
    
    print("📤 Minimal Request payload:")
    print(json.dumps(minimal_payload, indent=2))
    print()
    
    try:
        response = requests.post(
            ANALYZE_ENDPOINT,
            json=minimal_payload,
            headers={'Content-Type': 'application/json'},
            timeout=10
        )
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("✅ Success! Response:")
            print(json.dumps(response_data, indent=2))
            return True
        else:
            print(f"❌ Error {response.status_code}:")
            try:
                error_data = response.json()
                print(json.dumps(error_data, indent=2))
            except:
                print(response.text)
                
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")
        
    return False

def check_recent_responses():
    """Check what responses were created"""
    
    print("\n🔍 Checking recent LLM responses...")
    print("=" * 40)
    
    try:
        # Get recent responses via API
        responses_url = f"{BASE_URL}/api/llm-responses?limit=5"
        response = requests.get(responses_url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            responses = data.get('responses', [])
            
            print(f"📊 Found {len(responses)} recent responses:")
            for resp in responses:
                print(f"  ID: {resp.get('id')}, Status: {resp.get('status')}, Task: {resp.get('task_id', 'N/A')[:8]}...")
                
        else:
            print(f"❌ Failed to get responses: {response.status_code}")
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Request failed: {e}")

def main():
    """Main test function"""
    print("🧪 DocumentEvaluator API Test - Minimal Schema")
    print("=" * 50)
    
    # Test minimal payload
    success = test_with_minimal_payload()
    
    # Check what was created
    if success:
        time.sleep(2)  # Give it a moment to process
        check_recent_responses()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Minimal test completed successfully!")
    else:
        print("❌ Minimal test failed!")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
