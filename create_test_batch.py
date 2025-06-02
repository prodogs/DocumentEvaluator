#!/usr/bin/env python3
"""
Script to create a test batch with proper config snapshot
"""

import sys
import os
sys.path.append('server')

from services.batch_service import BatchService
import json

def main():
    try:
        batch_service = BatchService()
        
        # Create a new batch with folder 3
        result = batch_service.create_multi_folder_batch(
            folder_ids=[3],
            batch_name="Test Batch with Full Config",
            description="Test batch to verify RAG service integration"
        )
        
        if result:
            print("✅ Batch created successfully!")
            print(f"Batch ID: {result.get('id')}")
            print(f"Batch Number: {result.get('batch_number')}")
            print(f"Status: {result.get('status')}")
            
            # Print config snapshot connections
            config_snapshot = result.get('config_snapshot', {})
            connections = config_snapshot.get('connections', [])
            print(f"\nConnections in config snapshot: {len(connections)}")
            for conn in connections:
                print(f"  - ID: {conn.get('id')}, Name: {conn.get('name')}")
                print(f"    Base URL: {conn.get('base_url')}")
                print(f"    Model: {conn.get('model_name')}")
                print(f"    Provider: {conn.get('provider_type')}")
                
        else:
            print("❌ Failed to create batch")
            
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
