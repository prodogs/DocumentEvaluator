#!/usr/bin/env python3
"""
Debug Folder Scanning Issue

Check why only 1 document is being found when there should be 159
"""

import sys
import os
sys.path.append('/Users/frankfilippis/GitHub/DocumentEvaluator')

from server.database import Session
from server.models import Folder
import glob

def debug_folder_scanning():
    """Debug why folders aren't being scanned properly"""
    
    print("🔍 Folder Scanning Debug")
    print("=" * 40)
    
    session = Session()
    
    try:
        # Get all active folders
        folders = session.query(Folder).filter(Folder.active == 1).all()
        
        print(f"📊 Active Folders: {len(folders)}")
        print()
        
        total_files_found = 0
        
        for folder in folders:
            print(f"🗂️  Folder ID: {folder.id}")
            print(f"   Name: {folder.folder_name}")
            print(f"   Path: {folder.folder_path}")
            print(f"   Active: {folder.active}")
            
            # Check if path exists
            if not os.path.exists(folder.folder_path):
                print(f"   ❌ PATH DOES NOT EXIST!")
                continue
            
            # Check if it's a directory
            if not os.path.isdir(folder.folder_path):
                print(f"   ❌ PATH IS NOT A DIRECTORY!")
                continue
            
            print(f"   ✅ Path exists and is a directory")
            
            # Try different methods to find files
            print(f"   🔍 Scanning for files...")
            
            # Method 1: os.listdir
            try:
                all_files = os.listdir(folder.folder_path)
                print(f"   📁 Total items in directory: {len(all_files)}")
                
                # Filter for document files
                doc_extensions = ['.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.md']
                doc_files = [f for f in all_files if any(f.lower().endswith(ext) for ext in doc_extensions)]
                print(f"   📄 Document files found: {len(doc_files)}")
                
                if doc_files:
                    print(f"   📋 Sample files:")
                    for i, file in enumerate(doc_files[:5]):
                        full_path = os.path.join(folder.folder_path, file)
                        size = os.path.getsize(full_path) if os.path.exists(full_path) else 0
                        print(f"      {i+1}. {file} ({size} bytes)")
                    
                    if len(doc_files) > 5:
                        print(f"      ... and {len(doc_files) - 5} more files")
                
                total_files_found += len(doc_files)
                
            except Exception as e:
                print(f"   ❌ Error scanning directory: {e}")
            
            # Method 2: glob pattern matching
            try:
                patterns = ['*.pdf', '*.txt', '*.doc', '*.docx', '*.xls', '*.xlsx']
                glob_files = []
                
                for pattern in patterns:
                    pattern_path = os.path.join(folder.folder_path, pattern)
                    matches = glob.glob(pattern_path)
                    glob_files.extend(matches)
                
                print(f"   🔍 Glob pattern matches: {len(glob_files)}")
                
            except Exception as e:
                print(f"   ❌ Error with glob: {e}")
            
            # Method 3: Check specific known files
            if folder.id == 2:  # Cube folder
                known_files = [
                    'CUBE ERROR CODES - ENGLISH.pdf',
                    'CUBE ERROR CODES - ENGLISH.xls', 
                    'CUBE ERRORS.pdf'
                ]
                print(f"   🔍 Checking known Cube files:")
                for file in known_files:
                    full_path = os.path.join(folder.folder_path, file)
                    exists = os.path.exists(full_path)
                    print(f"      {file}: {'✅' if exists else '❌'}")
            
            elif folder.id == 3:  # VLMs folder
                print(f"   🔍 Checking VLM error files:")
                sample_files = [
                    'EN-Error 1 Not running Emergency button pressed.pdf',
                    'EN-Error 10 - CAN Error - Agile Inverter 1.pdf'
                ]
                for file in sample_files:
                    full_path = os.path.join(folder.folder_path, file)
                    exists = os.path.exists(full_path)
                    print(f"      {file}: {'✅' if exists else '❌'}")
            
            print()
        
        print(f"📊 SUMMARY:")
        print(f"   Total folders: {len(folders)}")
        print(f"   Total files found: {total_files_found}")
        print(f"   Expected files: 159 (1 + 2 + 155)")
        
        if total_files_found != 159:
            print(f"   ⚠️  MISMATCH: Found {total_files_found}, expected 159")
        else:
            print(f"   ✅ File count matches expectation")
        
        session.close()
        return total_files_found
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.close()
        return 0

def check_process_folder_logic():
    """Check how process_folder scans for files"""
    
    print(f"\n🔍 Process Folder Logic Check")
    print("=" * 35)
    
    # Simulate the file scanning logic from process_folder
    try:
        session = Session()
        folders = session.query(Folder).filter(Folder.active == 1).all()
        
        for folder in folders:
            folder_path = folder.folder_path
            print(f"\n📁 Scanning: {folder_path}")
            
            if not os.path.exists(folder_path):
                print(f"   ❌ Path doesn't exist")
                continue
            
            # This is the logic from process_folder.py
            files = []
            for root, dirs, filenames in os.walk(folder_path):
                for filename in filenames:
                    if filename.lower().endswith(('.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.md')):
                        file_path = os.path.join(root, filename)
                        files.append(file_path)
            
            print(f"   📄 Files found by os.walk: {len(files)}")
            
            if files:
                print(f"   📋 Sample files:")
                for i, file_path in enumerate(files[:3]):
                    filename = os.path.basename(file_path)
                    print(f"      {i+1}. {filename}")
        
        session.close()
        
    except Exception as e:
        print(f"❌ Error: {e}")

def main():
    """Main function"""
    
    print("🚀 Folder Scanning Debug")
    print("=" * 50)
    
    # Debug folder scanning
    total_found = debug_folder_scanning()
    
    # Check process folder logic
    check_process_folder_logic()
    
    print(f"\n" + "=" * 50)
    if total_found < 159:
        print(f"🔴 PROBLEM IDENTIFIED:")
        print(f"   Only {total_found} files found, expected 159")
        print(f"   This explains why only 1 document is in the database")
        print(f"   Need to investigate folder paths and file accessibility")
    else:
        print(f"✅ Files are accessible - issue may be in processing logic")

if __name__ == "__main__":
    main()
