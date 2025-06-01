#!/usr/bin/env python3
"""
Test script for snapshot API endpoints
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:5001"
STATS_ENDPOINT = f"{BASE_URL}/api/maintenance/stats"
SNAPSHOT_ENDPOINT = f"{BASE_URL}/api/maintenance/snapshot"
SNAPSHOT_STATUS_ENDPOINT = f"{BASE_URL}/api/maintenance/snapshot/status"
SNAPSHOTS_LIST_ENDPOINT = f"{BASE_URL}/api/maintenance/snapshots"

def test_enhanced_stats():
    """Test the enhanced maintenance stats endpoint"""
    print("🧪 Testing enhanced maintenance stats endpoint...")
    print("=" * 50)
    
    try:
        response = requests.get(STATS_ENDPOINT, timeout=10)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Enhanced Stats Response:")
            print(json.dumps(data, indent=2))
            
            if 'stats' in data:
                stats = data['stats']
                print(f"\n📈 Current Database State:")
                print(f"  LLM Responses: {stats.get('llm_responses', 0):,}")
                print(f"  Documents: {stats.get('documents', 0):,}")
                print(f"  Docs (Content): {stats.get('docs', 0):,}")
                print(f"  Connections: {stats.get('connections', 0):,}")
                print(f"  Models: {stats.get('models', 0):,}")
                print(f"  Providers: {stats.get('providers', 0):,}")
                print(f"  Batches: {stats.get('batches', 0):,}")
                print(f"  Snapshots: {stats.get('snapshots', 0):,}")
                print(f"  Total Records: {data.get('total_records', 0):,}")
                
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

def test_snapshot_creation():
    """Test creating a database snapshot"""
    print("\n🧪 Testing snapshot creation...")
    print("=" * 50)
    
    # Test payload
    snapshot_payload = {
        "name": "test_snapshot",
        "description": "Test snapshot created by API test"
    }
    
    print("📤 Snapshot Request payload:")
    print(json.dumps(snapshot_payload, indent=2))
    print()
    
    try:
        response = requests.post(SNAPSHOT_ENDPOINT, json=snapshot_payload, timeout=10)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 202:  # Accepted
            data = response.json()
            print("✅ Snapshot creation started!")
            print(json.dumps(data, indent=2))
            
            task_id = data.get('task_id')
            if task_id:
                print(f"\n🔍 Task ID: {task_id}")
                
                # Poll for status updates
                print("📊 Polling for status updates...")
                for i in range(10):  # Poll for up to 10 iterations
                    time.sleep(2)  # Wait 2 seconds between polls
                    
                    try:
                        status_response = requests.get(f"{SNAPSHOT_STATUS_ENDPOINT}/{task_id}", timeout=10)
                        
                        if status_response.status_code == 200:
                            status_data = status_response.json()
                            print(f"Poll {i+1}: Progress {status_data.get('progress', 0)}% - {status_data.get('step_name', 'Unknown')}")
                            
                            # Check if completed
                            if status_data.get('status') in ['COMPLETED', 'ERROR']:
                                print(f"\n🏁 Snapshot finished with status: {status_data.get('status')}")
                                if status_data.get('status') == 'COMPLETED':
                                    snapshot_info = status_data.get('snapshot_info', {})
                                    print(f"📁 Snapshot file: {snapshot_info.get('file_path', 'Unknown')}")
                                    print(f"📊 File size: {snapshot_info.get('file_size', 0) / 1024 / 1024:.1f} MB")
                                    print(f"📈 Record counts: {json.dumps(snapshot_info.get('record_counts', {}), indent=2)}")
                                elif status_data.get('error'):
                                    print(f"❌ Error: {status_data.get('error')}")
                                break
                        else:
                            print(f"❌ Status check failed: {status_response.status_code}")
                            
                    except requests.exceptions.RequestException as e:
                        print(f"❌ Status poll failed: {e}")
                
                return True
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

def test_list_snapshots():
    """Test listing snapshots"""
    print("\n🧪 Testing snapshot listing...")
    print("=" * 50)
    
    try:
        response = requests.get(SNAPSHOTS_LIST_ENDPOINT, timeout=10)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Snapshots List:")
            
            snapshots = data.get('snapshots', [])
            print(f"📊 Total snapshots: {data.get('total_snapshots', 0)}")
            
            for i, snapshot in enumerate(snapshots):
                print(f"\n📸 Snapshot {i+1}:")
                print(f"  ID: {snapshot.get('id')}")
                print(f"  Name: {snapshot.get('name')}")
                print(f"  Description: {snapshot.get('description')}")
                print(f"  File Size: {snapshot.get('file_size', 0) / 1024 / 1024:.1f} MB")
                print(f"  Created: {snapshot.get('created_at')}")
                print(f"  Status: {snapshot.get('status')}")
                
                record_counts = snapshot.get('record_counts', {})
                if record_counts:
                    print(f"  Record Counts: {json.dumps(record_counts)}")
                
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
    print("🧪 DocumentEvaluator Snapshot API Test")
    print("=" * 50)
    
    # Check backend health first
    if not check_backend_health():
        print("❌ Backend is not running. Please start the backend first.")
        sys.exit(1)
    
    print()
    
    # Test enhanced stats endpoint
    stats_success = test_enhanced_stats()
    
    # Test snapshot creation
    snapshot_success = test_snapshot_creation()
    
    # Test listing snapshots
    list_success = test_list_snapshots()
    
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"  Enhanced Stats: {'✅ PASS' if stats_success else '❌ FAIL'}")
    print(f"  Snapshot Creation: {'✅ PASS' if snapshot_success else '❌ FAIL'}")
    print(f"  Snapshot Listing: {'✅ PASS' if list_success else '❌ FAIL'}")
    
    if stats_success and snapshot_success and list_success:
        print("\n🎉 All snapshot API tests passed!")
        print("💡 The snapshot functionality is ready for use.")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
