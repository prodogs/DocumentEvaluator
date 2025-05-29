#!/usr/bin/env python

'''
Test script to check the Flask server's available routes
'''

import requests
import sys

BACKEND_BASE_URL = "http://localhost:5001"

def test_health():
    """Test the health endpoint"""
    try:
        response = requests.get(f"{BACKEND_BASE_URL}/api/health")
        response.raise_for_status()
        print("Health endpoint is working")
        print(f"Response: {response.json()}")
        return True
    except Exception as e:
        print(f"Health endpoint test failed: {e}")
        return False

def test_process_db_folders():
    """Test the process-db-folders endpoint"""
    try:
        print("\nTesting /process-db-folders endpoint...")
        response = requests.post(f"{BACKEND_BASE_URL}/process-db-folders")
        print(f"Status code: {response.status_code}")
        print(f"Response: {response.text}")

        if response.status_code == 200:
            print("process-db-folders endpoint is working")
            return True
        else:
            print(f"process-db-folders returned status {response.status_code}")
            return False
    except Exception as e:
        print(f"process-db-folders test failed: {e}")
        return False

def main():
    """Run tests on the server"""
    print(f"Testing server at {BACKEND_BASE_URL}")

    # Test if server is running at all
    try:
        health_response = requests.get(f"{BACKEND_BASE_URL}/api/health")
        print(f"Server is running. Status code from health check: {health_response.status_code}")
    except requests.exceptions.ConnectionError:
        print("ERROR: Could not connect to the server. Make sure it's running.")
        return 1

    # Print all available routes
    print("\nChecking available routes...")
    try:
        # Try to get Swagger API docs which should list available endpoints
        swagger_response = requests.get(f"{BACKEND_BASE_URL}/static/swagger.json")
        if swagger_response.status_code == 200:
            swagger_data = swagger_response.json()
            print("Available routes according to Swagger:")
            for path in swagger_data.get('paths', {}).keys():
                print(f"  {path}")
        else:
            print("Could not get swagger.json to list routes")
    except Exception as e:
        print(f"Error checking swagger routes: {e}")

    # Run specific endpoint tests
    tests = [
        ("Health check", test_health),
        ("Process DB folders", test_process_db_folders)
    ]

    print("\nRunning endpoint tests:")
    success_count = 0
    for name, test_func in tests:
        print(f"\n--- Testing {name} ---")
        if test_func():
            success_count += 1
            print(f"✅ {name} test passed")
        else:
            print(f"❌ {name} test failed")

    print(f"\n{success_count}/{len(tests)} tests passed")
    return 0 if success_count == len(tests) else 1

if __name__ == "__main__":
    sys.exit(main())
