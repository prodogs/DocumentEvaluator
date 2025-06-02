#!/usr/bin/env python3
"""Simple debug script to test batch 70 API endpoint"""

import urllib.request
import urllib.error
import json

API_BASE_URL = "http://localhost:5001"

def test_batch_endpoint():
    """Test the batch API endpoint"""
    print("=== Testing Batch 70 API Endpoint ===")
    
    # Test batch details endpoint
    try:
        url = f"{API_BASE_URL}/api/batches/70"
        print(f"Requesting: {url}")
        
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/json')
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"Status Code: {response.status}")
            print(f"Success: {data.get('success')}")
            
            if data.get('batch'):
                batch = data['batch']
                print(f"\nBatch Details:")
                print(json.dumps(batch, indent=2))
            else:
                print("No batch data in response")
                print(f"Full response: {json.dumps(data, indent=2)}")
                
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"Response: {e.read().decode('utf-8')}")
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
        print("\n⚠️  Cannot connect to server at localhost:5001")
        print("Make sure the server is running: cd server && python app.py")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

def test_llm_responses_endpoint():
    """Test the LLM responses endpoint"""
    print("\n=== Testing Batch 70 LLM Responses ===")
    
    try:
        url = f"{API_BASE_URL}/api/batches/70/llm-responses?limit=5&offset=0"
        print(f"Requesting: {url}")
        
        req = urllib.request.Request(url)
        req.add_header('Accept', 'application/json')
        
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
            print(f"Status Code: {response.status}")
            print(f"Success: {data.get('success')}")
            
            if data.get('pagination'):
                print(f"Total Responses: {data['pagination'].get('total', 0)}")
                
            if data.get('responses'):
                print(f"Found {len(data['responses'])} responses")
            else:
                print("No responses found")
                
    except urllib.error.HTTPError as e:
        print(f"HTTP Error {e.code}: {e.reason}")
        print(f"Response: {e.read().decode('utf-8')}")
    except urllib.error.URLError as e:
        print(f"URL Error: {e.reason}")
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")

def check_recent_logs():
    """Check recent logs for batch 70"""
    print("\n=== Recent Log Entries ===")
    
    import subprocess
    try:
        # Get recent log entries
        result = subprocess.run(
            ["tail", "-n", "100", "server/app.log"],
            capture_output=True,
            text=True,
            cwd="/Users/frankfilippis/AI/Github/DocumentEvaluator"
        )
        
        lines = result.stdout.split('\n')
        batch_70_lines = []
        
        for line in lines:
            if 'batches/70' in line or 'batch 70' in line.lower() or 'batch_id=70' in line:
                batch_70_lines.append(line)
                
        if batch_70_lines:
            print(f"Found {len(batch_70_lines)} log entries for batch 70:")
            for line in batch_70_lines[-10:]:  # Last 10 entries
                print(line)
        else:
            print("No recent log entries found for batch 70")
            
    except Exception as e:
        print(f"Error reading logs: {e}")

if __name__ == "__main__":
    print("Debugging Batch 70 Loading Issue")
    print("=" * 50)
    
    test_batch_endpoint()
    test_llm_responses_endpoint()
    check_recent_logs()