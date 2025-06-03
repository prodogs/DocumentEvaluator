#!/usr/bin/env python3
"""Test the unified batch service implementation"""

import requests
import json

BASE_URL = "http://localhost:5001/api"

def test_save_batch():
    """Test saving a batch without staging"""
    print("\n=== Testing Save Batch ===")
    
    data = {
        "batch_name": "Test Save Batch",
        "folder_ids": [1],
        "connection_ids": [1],
        "prompt_ids": [1],
        "meta_data": {"test": "save"}
    }
    
    response = requests.post(f"{BASE_URL}/batches/save", json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json()

def test_stage_batch():
    """Test staging a batch"""
    print("\n=== Testing Stage Batch ===")
    
    data = {
        "batch_name": "Test Stage Batch",
        "folder_ids": [1],
        "connection_ids": [1],
        "prompt_ids": [1],
        "meta_data": {"test": "stage"}
    }
    
    response = requests.post(f"{BASE_URL}/batches/stage", json=data)
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json()

def test_restage_batch(batch_id):
    """Test restaging an existing batch"""
    print(f"\n=== Testing Restage Batch {batch_id} ===")
    
    response = requests.post(f"{BASE_URL}/batches/{batch_id}/reprocess-staging")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json()

def test_batch_progress(batch_id):
    """Test getting batch progress"""
    print(f"\n=== Testing Batch Progress {batch_id} ===")
    
    response = requests.get(f"{BASE_URL}/batches/{batch_id}/progress")
    print(f"Status Code: {response.status_code}")
    print(f"Response: {json.dumps(response.json(), indent=2)}")
    
    return response.json()

def main():
    """Run all tests"""
    print("Testing Unified Batch Service Implementation")
    print("=" * 50)
    
    try:
        # Test save batch
        save_result = test_save_batch()
        
        # Test stage batch
        stage_result = test_stage_batch()
        
        # If staging was successful, test restaging
        if stage_result.get('success') and stage_result.get('batch_id'):
            batch_id = stage_result['batch_id']
            test_restage_batch(batch_id)
            test_batch_progress(batch_id)
        
        print("\n✅ All tests completed!")
        
    except Exception as e:
        print(f"\n❌ Error during testing: {e}")

if __name__ == "__main__":
    main()