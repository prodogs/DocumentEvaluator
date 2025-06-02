#!/usr/bin/env python3
"""Debug script to test batch 70 API endpoint and database"""

import requests
import psycopg2
import json
from datetime import datetime

API_BASE_URL = "http://localhost:5001"

def test_api_endpoint():
    """Test the batch API endpoint"""
    print("=== Testing Batch API Endpoint ===")
    
    # Test batch details endpoint
    try:
        response = requests.get(f"{API_BASE_URL}/api/batches/70")
        print(f"Status Code: {response.status_code}")
        print(f"Response Headers: {dict(response.headers)}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            if data.get('batch'):
                batch = data['batch']
                print(f"\nBatch Details:")
                for key, value in batch.items():
                    print(f"  {key}: {value}")
            else:
                print("No batch data in response")
        else:
            print(f"Error Response: {response.text}")
            
    except requests.exceptions.ConnectionError:
        print("ERROR: Cannot connect to server at localhost:5001")
        print("Make sure the server is running: cd server && python app.py")
        return False
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        return False
        
    # Test LLM responses endpoint
    print("\n=== Testing LLM Responses Endpoint ===")
    try:
        response = requests.get(f"{API_BASE_URL}/api/batches/70/llm-responses?limit=5&offset=0")
        print(f"Status Code: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"Success: {data.get('success')}")
            print(f"Total Responses: {data.get('pagination', {}).get('total', 0)}")
            if data.get('responses'):
                print(f"Found {len(data['responses'])} responses")
        else:
            print(f"Error Response: {response.text}")
            
    except Exception as e:
        print(f"ERROR: {type(e).__name__}: {e}")
        
    return True

def test_database():
    """Test direct database connection"""
    print("\n=== Testing Database Connection ===")
    
    try:
        # Connect to doc_eval database
        conn = psycopg2.connect(
            host="studio.local",
            database="doc_eval",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        cursor = conn.cursor()
        
        # Check if batch 70 exists
        cursor.execute("""
            SELECT id, batch_number, batch_name, status, created_at, 
                   total_documents, processed_documents, config_snapshot
            FROM batches 
            WHERE id = 70
        """)
        
        result = cursor.fetchone()
        if result:
            print("Batch 70 found in database:")
            print(f"  ID: {result[0]}")
            print(f"  Batch Number: {result[1]}")
            print(f"  Batch Name: {result[2]}")
            print(f"  Status: {result[3]}")
            print(f"  Created At: {result[4]}")
            print(f"  Total Documents: {result[5]}")
            print(f"  Processed Documents: {result[6]}")
            print(f"  Has Config Snapshot: {'Yes' if result[7] else 'No'}")
            
            # Check documents for this batch
            cursor.execute("SELECT COUNT(*) FROM documents WHERE batch_id = 70")
            doc_count = cursor.fetchone()[0]
            print(f"  Documents in batch: {doc_count}")
            
            # Check folder_ids
            cursor.execute("SELECT folder_ids FROM batches WHERE id = 70")
            folder_ids = cursor.fetchone()[0]
            print(f"  Folder IDs: {folder_ids}")
            
        else:
            print("Batch 70 NOT found in database!")
            
        cursor.close()
        conn.close()
        
    except Exception as e:
        print(f"Database Error: {type(e).__name__}: {e}")
        return False
        
    return True

def check_recent_errors():
    """Check app.log for recent errors"""
    print("\n=== Checking Recent Log Errors ===")
    
    try:
        import subprocess
        # Get last 20 lines mentioning batch 70 or errors
        result = subprocess.run(
            ["tail", "-n", "500", "server/app.log"],
            capture_output=True,
            text=True,
            cwd="/Users/frankfilippis/AI/Github/DocumentEvaluator"
        )
        
        lines = result.stdout.split('\n')
        relevant_lines = []
        
        for i, line in enumerate(lines):
            if 'batch 70' in line.lower() or 'batch/70' in line or 'batch_id=70' in line:
                # Get context (2 lines before and after)
                start = max(0, i-2)
                end = min(len(lines), i+3)
                relevant_lines.extend(lines[start:end])
                relevant_lines.append("---")
                
        if relevant_lines:
            print("Found log entries related to batch 70:")
            for line in relevant_lines[-50:]:  # Last 50 relevant lines
                print(line)
        else:
            print("No recent log entries found for batch 70")
            
    except Exception as e:
        print(f"Error reading logs: {e}")

if __name__ == "__main__":
    print("Debugging Batch 70 Loading Issue")
    print("=" * 50)
    
    # First check if server is running
    server_running = test_api_endpoint()
    
    # Test database regardless
    test_database()
    
    # Check logs
    check_recent_errors()
    
    if not server_running:
        print("\n⚠️  Server is not running. Start it with:")
        print("   cd server && python app.py")