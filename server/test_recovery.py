#!/usr/bin/env python3
"""
Test script to verify startup recovery functionality
"""

import requests
import json
import time
import sys

BASE_URL = "http://localhost:5001"

def test_recovery_status():
    """Test getting recovery status"""
    print("\n1. Testing recovery status endpoint...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/maintenance/recovery/status")
        
        if response.status_code == 200:
            data = response.json()
            print("✓ Recovery status retrieved successfully")
            print(f"  Recovery summary: {json.dumps(data['recovery_summary'], indent=2)}")
        else:
            print(f"✗ Failed to get recovery status: {response.status_code}")
            print(f"  Response: {response.text}")
            
    except Exception as e:
        print(f"✗ Error: {e}")


def test_manual_recovery():
    """Test manually triggering recovery"""
    print("\n2. Testing manual recovery trigger...")
    
    try:
        # Trigger recovery
        response = requests.post(f"{BASE_URL}/api/maintenance/recovery/run")
        
        if response.status_code == 202:
            data = response.json()
            task_id = data['task_id']
            print(f"✓ Recovery started with task ID: {task_id}")
            
            # Poll for completion
            print("  Monitoring recovery progress...")
            max_attempts = 30
            attempt = 0
            
            while attempt < max_attempts:
                time.sleep(1)
                status_response = requests.get(f"{BASE_URL}/api/maintenance/recovery/task/{task_id}")
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    progress = status_data['progress']
                    status = status_data['status']
                    step_name = status_data['step_name']
                    
                    print(f"  [{progress}%] {step_name}")
                    
                    if status == 'COMPLETED':
                        print("✓ Recovery completed successfully!")
                        results = status_data.get('recovery_results', {})
                        print(f"  Batches recovered: {results.get('batches_recovered', 0)}")
                        print(f"  Documents recovered: {results.get('documents_recovered', 0)}")
                        print(f"  Tasks recovered: {results.get('tasks_recovered', 0)}")
                        break
                    elif status == 'FAILED':
                        print(f"✗ Recovery failed: {status_data.get('error', 'Unknown error')}")
                        break
                        
                attempt += 1
                
            if attempt >= max_attempts:
                print("✗ Recovery timed out")
                
        else:
            print(f"✗ Failed to start recovery: {response.status_code}")
            print(f"  Response: {response.text}")
            
    except Exception as e:
        print(f"✗ Error: {e}")


def check_stuck_batches():
    """Check for batches stuck in ANALYZING or STAGING status"""
    print("\n3. Checking for stuck batches...")
    
    try:
        response = requests.get(f"{BASE_URL}/api/batches")
        
        if response.status_code == 200:
            data = response.json()
            batches = data.get('batches', [])
            
            stuck_batches = [b for b in batches if b.get('status') in ['ANALYZING', 'STAGING']]
            
            if stuck_batches:
                print(f"⚠️  Found {len(stuck_batches)} stuck batches:")
                for batch in stuck_batches:
                    print(f"   - Batch {batch['id']}: {batch['batch_name']} (status: {batch['status']})")
            else:
                print("✓ No stuck batches found")
                
        else:
            print(f"✗ Failed to get batches: {response.status_code}")
            
    except Exception as e:
        print(f"✗ Error: {e}")


def main():
    """Run all tests"""
    print("=" * 60)
    print("Testing Startup Recovery Functionality")
    print("=" * 60)
    
    # First check if server is running
    try:
        response = requests.get(f"{BASE_URL}/api/health")
        if response.status_code != 200:
            print("✗ Server is not responding. Please start the server first.")
            sys.exit(1)
    except:
        print("✗ Cannot connect to server at", BASE_URL)
        print("  Please ensure the server is running: python app.py")
        sys.exit(1)
    
    # Run tests
    check_stuck_batches()
    test_recovery_status()
    test_manual_recovery()
    
    print("\n" + "=" * 60)
    print("Recovery testing completed")
    print("=" * 60)


if __name__ == "__main__":
    main()