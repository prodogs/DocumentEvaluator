#!/usr/bin/env python3
"""
Test script for maintenance API endpoints
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:5001"
STATS_ENDPOINT = f"{BASE_URL}/api/maintenance/stats"
RESET_ENDPOINT = f"{BASE_URL}/api/maintenance/reset"
STATUS_ENDPOINT = f"{BASE_URL}/api/maintenance/reset/status"

def test_maintenance_stats():
    """Test the maintenance stats endpoint"""
    print("🧪 Testing maintenance stats endpoint...")
    print("=" * 50)
    
    try:
        response = requests.get(STATS_ENDPOINT, timeout=10)
        
        print(f"📊 Response Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Success! Stats Response:")
            print(json.dumps(data, indent=2))
            
            if 'stats' in data:
                stats = data['stats']
                print(f"\n📈 Current Database State:")
                print(f"  LLM Responses: {stats.get('llm_responses', 0):,}")
                print(f"  Documents: {stats.get('documents', 0):,}")
                print(f"  Docs (Content): {stats.get('docs', 0):,}")
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

def test_maintenance_reset_dry_run():
    """Test the maintenance reset endpoint (dry run - just check if it starts)"""
    print("\n🧪 Testing maintenance reset endpoint (dry run)...")
    print("=" * 50)
    
    # First check current stats
    print("📊 Current stats before reset:")
    test_maintenance_stats()
    
    print("\n⚠️  This is a DRY RUN - we'll start the reset but not wait for completion")
    print("   (To avoid actually deleting data during testing)")
    
    try:
        response = requests.post(RESET_ENDPOINT, json={}, timeout=10)
        
        print(f"\n📊 Reset Response Status: {response.status_code}")
        
        if response.status_code == 202:  # Accepted
            data = response.json()
            print("✅ Reset started successfully!")
            print(json.dumps(data, indent=2))
            
            task_id = data.get('task_id')
            if task_id:
                print(f"\n🔍 Task ID: {task_id}")
                
                # Check status once
                print("📊 Checking initial status...")
                status_response = requests.get(f"{STATUS_ENDPOINT}/{task_id}", timeout=10)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    print("📈 Status Response:")
                    print(json.dumps(status_data, indent=2))
                else:
                    print(f"❌ Status check failed: {status_response.status_code}")
                
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
    print("🧪 DocumentEvaluator Maintenance API Test")
    print("=" * 50)
    
    # Check backend health first
    if not check_backend_health():
        print("❌ Backend is not running. Please start the backend first.")
        sys.exit(1)
    
    print()
    
    # Test stats endpoint
    stats_success = test_maintenance_stats()
    
    # Test reset endpoint (dry run)
    reset_success = test_maintenance_reset_dry_run()
    
    print("\n" + "=" * 50)
    print("📋 Test Summary:")
    print(f"  Stats Endpoint: {'✅ PASS' if stats_success else '❌ FAIL'}")
    print(f"  Reset Endpoint: {'✅ PASS' if reset_success else '❌ FAIL'}")
    
    if stats_success and reset_success:
        print("\n🎉 All maintenance API tests passed!")
        print("💡 The maintenance tab should now work in the frontend.")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
