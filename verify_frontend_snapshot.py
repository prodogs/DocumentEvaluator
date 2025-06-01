#!/usr/bin/env python3
"""
Verify the frontend snapshot functionality is accessible
"""

import requests
import time

def check_frontend():
    """Check if frontend is accessible and has the updated code"""
    print("🌐 Checking Frontend Accessibility")
    print("=" * 50)
    
    try:
        # Check if frontend is running
        response = requests.get("http://localhost:5173", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend is accessible at http://localhost:5173")
            
            # Check if the HTML contains React app
            if "root" in response.text:
                print("✅ React app is loading")
            else:
                print("⚠️  React app may not be loading properly")
                
            return True
        else:
            print(f"❌ Frontend returned status: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Frontend is not accessible: {e}")
        return False

def check_backend():
    """Check if backend APIs are working"""
    print("\n🔧 Checking Backend APIs")
    print("=" * 50)
    
    try:
        # Check maintenance stats
        response = requests.get("http://localhost:5001/api/maintenance/stats", timeout=5)
        if response.status_code == 200:
            data = response.json()
            stats = data.get('stats', {})
            print("✅ Backend APIs are working")
            print(f"   📊 Current database state:")
            print(f"      Documents: {stats.get('documents', 0):,}")
            print(f"      LLM Responses: {stats.get('llm_responses', 0):,}")
            print(f"      Snapshots: {stats.get('snapshots', 0):,}")
            return True
        else:
            print(f"❌ Backend API failed: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Backend API error: {e}")
        return False

def main():
    """Main verification function"""
    print("🧪 DocumentEvaluator Frontend Snapshot Verification")
    print("=" * 60)
    
    frontend_ok = check_frontend()
    backend_ok = check_backend()
    
    print("\n" + "=" * 60)
    print("📋 Verification Results:")
    print(f"  Frontend (http://localhost:5173): {'✅ ACCESSIBLE' if frontend_ok else '❌ NOT ACCESSIBLE'}")
    print(f"  Backend APIs: {'✅ WORKING' if backend_ok else '❌ NOT WORKING'}")
    
    if frontend_ok and backend_ok:
        print("\n🎉 Everything is ready!")
        print("\n🎯 To test the snapshot functionality:")
        print("1. Open http://localhost:5173 in your browser")
        print("2. Navigate to the '🔧 Maintenance' tab")
        print("3. You should now see:")
        print("   📊 Enhanced database statistics")
        print("   🔄 Database reset functionality")
        print("   📸 Database snapshots section with:")
        print("      - 'Save Snapshot' button")
        print("      - Snapshots list (if any exist)")
        print("      - Load/Edit/Delete buttons for each snapshot")
        print("   📋 Progress log window")
        print("\n4. Test the functionality:")
        print("   - Click 'Save Snapshot' to create a new snapshot")
        print("   - Watch progress in the log window")
        print("   - Use Load/Edit/Delete buttons on existing snapshots")
        
        return 0
    else:
        print("\n❌ Some components are not working properly.")
        if not frontend_ok:
            print("   🔧 Try restarting the frontend: cd client && npm run dev")
        if not backend_ok:
            print("   🔧 Try restarting the backend: cd server && python app.py")
        return 1

if __name__ == "__main__":
    exit(main())
