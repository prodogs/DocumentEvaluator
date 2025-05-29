#!/usr/bin/env python3
"""
Fix VLM Folder Configuration

Update the folder path to point to the actual directory with files
"""

import sys
import os
sys.path.append('/Users/frankfilippis/GitHub/DocumentEvaluator')

from server.database import Session
from server.models import Folder

def fix_vlm_folder():
    """Fix the VLM folder configuration"""
    
    print("🔧 Fixing VLM Folder Configuration")
    print("=" * 40)
    
    session = Session()
    
    try:
        # Find the VLM folder (ID 3)
        vlm_folder = session.query(Folder).filter(Folder.id == 3).first()
        
        if not vlm_folder:
            print("❌ VLM folder not found!")
            return False
        
        print(f"📍 Current Configuration:")
        print(f"   ID: {vlm_folder.id}")
        print(f"   Path: {vlm_folder.folder_path}")
        print(f"   Name: {vlm_folder.folder_name}")
        print(f"   Active: {vlm_folder.active}")
        
        # Check current path
        current_path = vlm_folder.folder_path
        new_path = os.path.join(current_path, "08 error list")
        
        print(f"\n🔍 Checking paths:")
        print(f"   Current: {current_path}")
        print(f"   New: {new_path}")
        
        # Check if new path exists and has files
        if os.path.exists(new_path):
            pdf_files = [f for f in os.listdir(new_path) if f.endswith('.pdf')]
            print(f"   ✅ New path exists with {len(pdf_files)} PDF files")
        else:
            print(f"   ❌ New path does not exist!")
            return False
        
        # Update the folder configuration
        print(f"\n🔄 Updating folder configuration...")
        vlm_folder.folder_path = new_path
        vlm_folder.folder_name = "08 VLMs - Error List"
        
        session.commit()
        
        print(f"✅ Updated folder configuration:")
        print(f"   ID: {vlm_folder.id}")
        print(f"   Path: {vlm_folder.folder_path}")
        print(f"   Name: {vlm_folder.folder_name}")
        print(f"   Active: {vlm_folder.active}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.rollback()
        session.close()
        return False

def verify_all_folders():
    """Verify all folder configurations"""
    
    print(f"\n📋 Verifying All Folder Configurations")
    print("=" * 45)
    
    session = Session()
    
    try:
        folders = session.query(Folder).filter(Folder.active == 1).all()
        
        total_files = 0
        
        for folder in folders:
            print(f"\nFolder ID: {folder.id}")
            print(f"  Name: {folder.folder_name}")
            print(f"  Path: {folder.folder_path}")
            
            if os.path.exists(folder.folder_path):
                files = [f for f in os.listdir(folder.folder_path) 
                        if f.endswith(('.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx'))]
                print(f"  Files: {len(files)}")
                total_files += len(files)
                
                if len(files) > 0:
                    print(f"  Sample: {files[0]}")
            else:
                print(f"  ⚠️  Path not found!")
        
        print(f"\n📊 Summary:")
        print(f"   Active folders: {len(folders)}")
        print(f"   Total files: {total_files}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.close()
        return False

def main():
    """Main function"""
    
    print("🚀 VLM Folder Fix")
    print("=" * 30)
    print("Host: tablemini.local:5432")
    print("Database: doc_eval")
    print()
    
    # Fix the VLM folder
    fix_ok = fix_vlm_folder()
    
    if fix_ok:
        # Verify all folders
        verify_ok = verify_all_folders()
        
        if verify_ok:
            print(f"\n✅ Folder configuration fixed!")
            print(f"💡 The VLM folder will now be processed in future runs.")
            print(f"🔄 Run process-db-folders again to process the 155 PDF files.")
        else:
            print(f"\n⚠️  Verification failed.")
    else:
        print(f"\n❌ Could not fix folder configuration.")

if __name__ == "__main__":
    main()
