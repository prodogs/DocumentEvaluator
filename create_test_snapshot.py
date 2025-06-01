#!/usr/bin/env python3
"""
Create a test snapshot to populate the UI with data
"""

import requests
import json
import time

BASE_URL = "http://localhost:5001"

def create_test_snapshot():
    """Create a test snapshot to see in the UI"""
    print("🧪 Creating Test Snapshot for UI Demo")
    print("=" * 50)
    
    snapshot_payload = {
        "name": "demo_snapshot",
        "description": "Demo snapshot to test the UI functionality"
    }
    
    try:
        print("📤 Creating snapshot...")
        response = requests.post(f"{BASE_URL}/api/maintenance/snapshot", json=snapshot_payload, timeout=10)
        
        if response.status_code == 202:
            data = response.json()
            task_id = data.get('task_id')
            print(f"✅ Snapshot creation started: {task_id[:8]}...")
            
            # Wait a bit for it to start
            print("⏳ Waiting for snapshot to complete...")
            print("   (This may take 30-60 seconds for the database dump)")
            
            # Check status a few times
            for i in range(15):  # Check for 30 seconds
                time.sleep(2)
                try:
                    status_response = requests.get(f"{BASE_URL}/api/maintenance/snapshot/status/{task_id}", timeout=5)
                    
                    if status_response.status_code == 200:
                        status_data = status_response.json()
                        progress = status_data.get('progress', 0)
                        step_name = status_data.get('step_name', 'Unknown')
                        print(f"   📊 Progress: {progress}% - {step_name}")
                        
                        if status_data.get('status') == 'COMPLETED':
                            print("   🎉 Snapshot completed!")
                            return True
                        elif status_data.get('status') == 'ERROR':
                            print(f"   ❌ Snapshot failed: {status_data.get('error')}")
                            return False
                except:
                    print(f"   📊 Checking status... (attempt {i+1})")
                    
            print("   ⏰ Still creating... (check the UI for progress)")
            return True
            
        else:
            print(f"❌ Failed to start snapshot: {response.status_code}")
            try:
                error_data = response.json()
                print(f"   Error: {error_data.get('error', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
            return False
            
    except Exception as e:
        print(f"❌ Error creating snapshot: {e}")
        return False

def check_snapshots():
    """Check if snapshots exist in the database"""
    print("\n🔍 Checking Existing Snapshots")
    print("=" * 50)
    
    try:
        response = requests.get(f"{BASE_URL}/api/maintenance/snapshots", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            snapshots = data.get('snapshots', [])
            print(f"📊 Found {len(snapshots)} snapshots in database")
            
            if snapshots:
                print("\n📸 Existing snapshots:")
                for i, snapshot in enumerate(snapshots):
                    print(f"   {i+1}. {snapshot.get('name')} ({(snapshot.get('file_size', 0) / 1024 / 1024):.1f} MB)")
                    print(f"      Status: {snapshot.get('status')}")
                    print(f"      Created: {snapshot.get('created_at')}")
                return True
            else:
                print("   No snapshots found in database")
                return False
        else:
            print(f"❌ Failed to check snapshots: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Error checking snapshots: {e}")
        return False

def main():
    """Main function"""
    print("🎯 DocumentEvaluator Snapshot UI Demo Setup")
    print("=" * 60)
    
    # Check existing snapshots first
    has_snapshots = check_snapshots()
    
    if not has_snapshots:
        print("\n💡 Creating a demo snapshot to populate the UI...")
        success = create_test_snapshot()
        
        if success:
            print("\n🎉 Demo snapshot creation initiated!")
        else:
            print("\n❌ Failed to create demo snapshot")
    else:
        print("\n✅ Snapshots already exist!")
    
    print("\n" + "=" * 60)
    print("🎯 Now test the UI functionality:")
    print("1. Refresh the maintenance tab in your browser")
    print("2. You should see snapshots in the grid with action buttons:")
    print("   🔄 Load - Restore database from snapshot")
    print("   ✏️ Edit - Change snapshot name/description")
    print("   🗑️ Delete - Remove snapshot permanently")
    print("3. Try creating a new snapshot with the 'Save Snapshot' button")
    print("4. Watch the progress in the log window")
    print("5. Test the Load/Edit/Delete functionality")
    
    print(f"\n🌐 Frontend: http://localhost:5173")
    print("📋 Navigate to: Maintenance tab → Database Snapshots section")

if __name__ == "__main__":
    main()
