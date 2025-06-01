#!/usr/bin/env python3
"""
Test script for analyze_document_with_llm endpoint with new schema
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:5001"
ANALYZE_ENDPOINT = f"{BASE_URL}/analyze_document_with_llm"
STATUS_ENDPOINT = f"{BASE_URL}/analyze_status"

def test_analyze_document_new_schema():
    """Test the analyze_document_with_llm endpoint with new schema"""
    
    print("🧪 Testing analyze_document_with_llm with new schema...")
    print("=" * 60)
    
    # Test payload using new schema (doc_id instead of file upload)
    test_payload = {
        "doc_id": 3187,  # Using existing document with doc_id
        "prompts": [
            {
                "prompt": "Analyze this document and provide a summary of the main points."
            },
            {
                "prompt": "What are the key technical details mentioned in this document?"
            }
        ],
        "llm_provider": {
            "provider_type": "ollama",
            "url": "http://studio.local",
            "model_name": "gemma3-latest",
            "api_key": None,
            "port_no": 11434
        },
        "meta_data": {
            "batch_context": "Test analysis with new schema",
            "test_run": True
        }
    }
    
    print("📤 Request payload:")
    print(json.dumps(test_payload, indent=2))
    print()
    
    try:
        # Send the request
        print("🚀 Sending request to analyze_document_with_llm...")
        response = requests.post(
            ANALYZE_ENDPOINT,
            json=test_payload,
            headers={'Content-Type': 'application/json'},
            timeout=30
        )
        
        print(f"📊 Response Status: {response.status_code}")
        print(f"📊 Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            response_data = response.json()
            print("✅ Success! Response:")
            print(json.dumps(response_data, indent=2))
            
            # Extract task_id for status polling
            task_id = response_data.get('task_id')
            if task_id:
                print(f"\n🔍 Task ID: {task_id}")
                print("📊 Polling for status updates...")
                poll_task_status(task_id)
            else:
                print("⚠️  No task_id in response")
                
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
    
    return response.status_code == 200

def poll_task_status(task_id, max_polls=10, poll_interval=2):
    """Poll the task status endpoint"""
    
    print(f"\n📊 Polling status for task: {task_id}")
    print("-" * 40)
    
    for i in range(max_polls):
        try:
            status_url = f"{STATUS_ENDPOINT}/{task_id}"
            response = requests.get(status_url, timeout=10)
            
            if response.status_code == 200:
                status_data = response.json()
                print(f"Poll {i+1}: {json.dumps(status_data, indent=2)}")
                
                # Check if processing is complete
                status = status_data.get('status', '')
                if status in ['completed', 'error', 'failed']:
                    print(f"🏁 Task finished with status: {status}")
                    break
                    
            else:
                print(f"❌ Status check failed: {response.status_code}")
                try:
                    error_data = response.json()
                    print(json.dumps(error_data, indent=2))
                except:
                    print(response.text)
                    
        except requests.exceptions.RequestException as e:
            print(f"❌ Status poll failed: {e}")
            
        if i < max_polls - 1:
            print(f"⏳ Waiting {poll_interval} seconds...")
            time.sleep(poll_interval)
    
    print("📊 Status polling complete")

def check_backend_health():
    """Check if backend is running"""
    try:
        health_url = f"{BASE_URL}/api/health"
        response = requests.get(health_url, timeout=5)
        if response.status_code == 200:
            print("✅ Backend is healthy")
            return True
        else:
            print(f"⚠️  Backend health check failed: {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Backend is not accessible: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 DocumentEvaluator API Test - New Schema")
    print("=" * 50)
    
    # Check backend health first
    if not check_backend_health():
        print("❌ Backend is not running. Please start the backend first.")
        sys.exit(1)
    
    print()
    
    # Run the test
    success = test_analyze_document_new_schema()
    
    print("\n" + "=" * 50)
    if success:
        print("✅ Test completed successfully!")
    else:
        print("❌ Test failed!")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
