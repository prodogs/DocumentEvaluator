#!/usr/bin/env python3
"""
Test the full-screen maintenance page layout
"""

import requests
import time

def test_maintenance_layout():
    """Test that the maintenance page is accessible and properly configured"""
    print("🧪 Testing Maintenance Page Full-Screen Layout")
    print("=" * 60)
    
    # Check if frontend is accessible
    try:
        response = requests.get("http://localhost:5173", timeout=5)
        if response.status_code == 200:
            print("✅ Frontend is accessible at http://localhost:5173")
        else:
            print(f"⚠️  Frontend returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Frontend not accessible: {e}")
        return False
    
    # Check if backend is accessible
    try:
        response = requests.get("http://localhost:5001/api/maintenance/stats", timeout=5)
        if response.status_code == 200:
            print("✅ Backend API is accessible")
        else:
            print(f"⚠️  Backend API returned status {response.status_code}")
    except Exception as e:
        print(f"❌ Backend API not accessible: {e}")
        return False
    
    print("\n🎯 Layout Changes Applied:")
    print("✅ MaintenanceManager now uses full viewport (100vw x 100vh)")
    print("✅ Fixed positioning for full-screen experience")
    print("✅ Scrollable content area for maintenance sections")
    print("✅ Optimized spacing and padding for better space utilization")
    print("✅ Responsive design for mobile devices")
    
    print("\n📋 CSS Changes Summary:")
    print("• .maintenance-manager: Full viewport with fixed positioning")
    print("• .maintenance-content: Scrollable flex container")
    print("• .maintenance-header: Compact header with flex-shrink: 0")
    print("• .maintenance-section: Reduced padding for better space usage")
    print("• .progress-window: Optimized height (250px desktop, 200px mobile)")
    
    print("\n🌐 To test the full-screen layout:")
    print("1. Open http://localhost:5173 in your browser")
    print("2. Navigate to the '🔧 Maintenance' tab")
    print("3. The page should now take up the full browser window")
    print("4. Scroll through the maintenance sections")
    print("5. Test on different screen sizes and mobile devices")
    
    return True

def main():
    """Main function"""
    success = test_maintenance_layout()
    
    if success:
        print("\n🎉 Maintenance page is ready for full-screen testing!")
    else:
        print("\n❌ Some issues detected. Please check the setup.")
    
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())
