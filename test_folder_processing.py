#!/usr/bin/env python3
"""
Test Folder Processing Loop

Test if the background processing loop is working correctly
"""

import sys
import os
sys.path.append('/Users/frankfilippis/GitHub/DocumentEvaluator')

from server.database import Session
from server.models import Folder
from server.api.process_folder import process_folder

def test_folder_processing():
    """Test processing each folder individually"""
    
    print("🔍 Testing Folder Processing")
    print("=" * 40)
    
    session = Session()
    
    try:
        # Get all active folders
        folders = session.query(Folder).filter(Folder.active == 1).all()
        
        print(f"📊 Found {len(folders)} active folders")
        print()
        
        for i, folder in enumerate(folders, 1):
            print(f"🗂️  Testing Folder {i}/{len(folders)}")
            print(f"   ID: {folder.id}")
            print(f"   Name: {folder.folder_name}")
            print(f"   Path: {folder.folder_path}")
            
            try:
                # Test process_folder function
                print(f"   🔄 Calling process_folder...")
                
                result = process_folder(
                    folder.folder_path,
                    task_id=f"test-{folder.id}",
                    batch_name=f"Test Batch {folder.id}",
                    folder_id=folder.id
                )
                
                print(f"   ✅ Success! Result: {result}")
                print(f"      Total Files: {result.get('totalFiles', 0)}")
                print(f"      Processed Files: {result.get('processedFiles', 0)}")
                
                if 'error' in result:
                    print(f"      ⚠️  Error in result: {result['error']}")
                
            except Exception as e:
                print(f"   ❌ Error processing folder: {e}")
                print(f"      This could be why the background loop stops!")
                import traceback
                traceback.print_exc()
            
            print()
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.close()

def test_background_loop_simulation():
    """Simulate the background processing loop"""
    
    print("🔄 Simulating Background Processing Loop")
    print("=" * 45)
    
    session = Session()
    
    try:
        folders = session.query(Folder).filter(Folder.active == 1).all()
        
        total_files = 0
        processed_files = 0
        
        print(f"📊 Starting loop with {len(folders)} folders")
        
        for i, folder in enumerate(folders, 1):
            print(f"\n🗂️  Loop iteration {i}: {folder.folder_name}")
            print(f"   Path: {folder.folder_path}")
            
            try:
                # This is the exact logic from routes.py
                result = process_folder(
                    folder.folder_path,
                    task_id=f"sim-{folder.id}",
                    batch_name="Simulation Test",
                    folder_id=folder.id
                )
                
                # Update counts (exact logic from routes.py)
                total_files += result.get('totalFiles', 0)
                processed_files += result.get('processedFiles', 0)
                
                print(f"   ✅ Folder processed successfully")
                print(f"      This folder: {result.get('totalFiles', 0)} total, {result.get('processedFiles', 0)} processed")
                print(f"      Running totals: {total_files} total, {processed_files} processed")
                
            except Exception as e:
                print(f"   ❌ Error processing folder {folder.folder_name}: {e}")
                print(f"      This would stop the entire background loop!")
                # In the actual code, this error is caught and logged, but the loop should continue
                import traceback
                traceback.print_exc()
                break  # This simulates what might be happening
        
        print(f"\n📊 Final Results:")
        print(f"   Total Files: {total_files}")
        print(f"   Processed Files: {processed_files}")
        print(f"   Expected: ~164 files across all folders")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error in simulation: {e}")
        session.close()

def main():
    """Main function"""
    
    print("🚀 Folder Processing Test")
    print("=" * 50)
    
    # Test individual folder processing
    test_folder_processing()
    
    # Test background loop simulation
    test_background_loop_simulation()
    
    print("\n" + "=" * 50)
    print("💡 If any folder fails, that explains why only 1 document")
    print("   is being processed instead of all 164 files!")

if __name__ == "__main__":
    main()
