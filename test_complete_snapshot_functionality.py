#!/usr/bin/env python3
"""
Complete test script for all snapshot functionality:
- Create snapshots
- List snapshots
- Load/restore snapshots
- Edit snapshot metadata
- Delete snapshots
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:5001"

def test_create_snapshot():
    """Test creating a snapshot"""
    print("🧪 Testing Snapshot Creation")
    print("=" * 40)
    
    snapshot_payload = {
        "name": "test_complete_functionality",
        "description": "Test snapshot for complete functionality testing"
    }
    
    try:
        response = requests.post(f"{BASE_URL}/api/maintenance/snapshot", json=snapshot_payload, timeout=10)
        
        if response.status_code == 202:
            data = response.json()
            task_id = data.get('task_id')
            print(f"✅ Snapshot creation started: {task_id[:8]}...")
            
            # Wait for completion
            for i in range(30):  # Wait up to 60 seconds
                time.sleep(2)
                status_response = requests.get(f"{BASE_URL}/api/maintenance/snapshot/status/{task_id}", timeout=10)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    progress = status_data.get('progress', 0)
                    step_name = status_data.get('step_name', 'Unknown')
                    print(f"   📊 Progress: {progress}% - {step_name}")
                    
                    if status_data.get('status') == 'COMPLETED':
                        print("   🎉 Snapshot created successfully!")
                        return status_data.get('snapshot_info', {}).get('id')
                    elif status_data.get('status') == 'ERROR':
                        print(f"   ❌ Snapshot failed: {status_data.get('error')}")
                        return None
                        
            print("   ⏰ Snapshot creation timed out")
            return None
        else:
            print(f"❌ Failed to start snapshot: {response.status_code}")
            return None
            
    except Exception as e:
        print(f"❌ Error creating snapshot: {e}")
        return None

def test_list_snapshots():
    """Test listing snapshots"""
    print("\n🧪 Testing Snapshot Listing")
    print("=" * 40)
    
    try:
        response = requests.get(f"{BASE_URL}/api/maintenance/snapshots", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            snapshots = data.get('snapshots', [])
            print(f"✅ Found {len(snapshots)} snapshots")
            
            for i, snapshot in enumerate(snapshots):
                print(f"\n📸 Snapshot {i+1}:")
                print(f"   ID: {snapshot.get('id')}")
                print(f"   Name: {snapshot.get('name')}")
                print(f"   Size: {(snapshot.get('file_size', 0) / 1024 / 1024):.1f} MB")
                print(f"   Status: {snapshot.get('status')}")
                
            return snapshots
        else:
            print(f"❌ Failed to list snapshots: {response.status_code}")
            return []
            
    except Exception as e:
        print(f"❌ Error listing snapshots: {e}")
        return []

def test_edit_snapshot(snapshot_id):
    """Test editing a snapshot"""
    print(f"\n🧪 Testing Snapshot Edit (ID: {snapshot_id})")
    print("=" * 40)
    
    update_data = {
        "name": "edited_test_snapshot",
        "description": "This snapshot has been edited via API test"
    }
    
    try:
        response = requests.patch(f"{BASE_URL}/api/maintenance/snapshot/{snapshot_id}", json=update_data, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Snapshot updated successfully!")
            print(f"   New name: {data.get('snapshot', {}).get('name')}")
            print(f"   New description: {data.get('snapshot', {}).get('description')}")
            return True
        else:
            print(f"❌ Failed to update snapshot: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error updating snapshot: {e}")
        return False

def test_load_snapshot(snapshot_id):
    """Test loading/restoring a snapshot"""
    print(f"\n🧪 Testing Snapshot Load (ID: {snapshot_id})")
    print("=" * 40)
    print("⚠️  WARNING: This will restore the database!")
    
    # Ask for confirmation
    confirm = input("Do you want to proceed with database restore? (y/N): ").lower().strip()
    if confirm != 'y':
        print("❌ Snapshot load test skipped by user")
        return False
    
    try:
        response = requests.post(f"{BASE_URL}/api/maintenance/snapshot/{snapshot_id}/load", timeout=10)
        
        if response.status_code == 202:
            data = response.json()
            task_id = data.get('task_id')
            print(f"✅ Restore operation started: {task_id[:8]}...")
            
            # Wait for completion
            for i in range(60):  # Wait up to 120 seconds
                time.sleep(2)
                status_response = requests.get(f"{BASE_URL}/api/maintenance/snapshot/status/{task_id}", timeout=10)
                
                if status_response.status_code == 200:
                    status_data = status_response.json()
                    progress = status_data.get('progress', 0)
                    step_name = status_data.get('step_name', 'Unknown')
                    print(f"   📊 Progress: {progress}% - {step_name}")
                    
                    if status_data.get('status') == 'COMPLETED':
                        print("   🎉 Database restore completed successfully!")
                        print(f"   📁 Backup created: {status_data.get('backup_created', 'Unknown')}")
                        return True
                    elif status_data.get('status') == 'ERROR':
                        print(f"   ❌ Restore failed: {status_data.get('error')}")
                        return False
                        
            print("   ⏰ Restore operation timed out")
            return False
        else:
            print(f"❌ Failed to start restore: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error loading snapshot: {e}")
        return False

def test_delete_snapshot(snapshot_id):
    """Test deleting a snapshot"""
    print(f"\n🧪 Testing Snapshot Delete (ID: {snapshot_id})")
    print("=" * 40)
    
    try:
        response = requests.delete(f"{BASE_URL}/api/maintenance/snapshot/{snapshot_id}", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print("✅ Snapshot deleted successfully!")
            print(f"   Message: {data.get('message')}")
            print(f"   File deleted: {data.get('file_deleted')}")
            return True
        else:
            print(f"❌ Failed to delete snapshot: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error deleting snapshot: {e}")
        return False

def main():
    """Main test function"""
    print("🧪 DocumentEvaluator Complete Snapshot Functionality Test")
    print("=" * 60)
    
    # Test 1: Create a snapshot
    snapshot_id = test_create_snapshot()
    if not snapshot_id:
        print("\n❌ Cannot continue tests without a snapshot")
        return 1
    
    # Test 2: List snapshots
    snapshots = test_list_snapshots()
    if not snapshots:
        print("\n❌ No snapshots found")
        return 1
    
    # Use the first snapshot for remaining tests
    test_snapshot = snapshots[0]
    test_id = test_snapshot.get('id')
    
    # Test 3: Edit snapshot
    edit_success = test_edit_snapshot(test_id)
    
    # Test 4: Load snapshot (optional, requires user confirmation)
    load_success = test_load_snapshot(test_id)
    
    # Test 5: Delete snapshot (ask for confirmation)
    print(f"\n🗑️ Delete Test Snapshot?")
    delete_confirm = input(f"Delete snapshot '{test_snapshot.get('name')}'? (y/N): ").lower().strip()
    delete_success = False
    if delete_confirm == 'y':
        delete_success = test_delete_snapshot(test_id)
    else:
        print("❌ Snapshot deletion skipped by user")
    
    # Summary
    print("\n" + "=" * 60)
    print("📋 Test Summary:")
    print(f"  Create Snapshot: {'✅ PASS' if snapshot_id else '❌ FAIL'}")
    print(f"  List Snapshots: {'✅ PASS' if snapshots else '❌ FAIL'}")
    print(f"  Edit Snapshot: {'✅ PASS' if edit_success else '❌ FAIL'}")
    print(f"  Load Snapshot: {'✅ PASS' if load_success else '⏭️ SKIPPED'}")
    print(f"  Delete Snapshot: {'✅ PASS' if delete_success else '⏭️ SKIPPED'}")
    
    print("\n🎯 Frontend Testing:")
    print("1. Open http://localhost:5173")
    print("2. Navigate to '🔧 Maintenance' tab")
    print("3. Test all snapshot operations:")
    print("   - Create new snapshots")
    print("   - View snapshot list with action buttons")
    print("   - Edit snapshot names/descriptions")
    print("   - Load snapshots (restore database)")
    print("   - Delete snapshots")
    print("4. Monitor progress in the log window")
    
    return 0

if __name__ == "__main__":
    sys.exit(main())
