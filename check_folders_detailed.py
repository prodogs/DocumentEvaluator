#!/usr/bin/env python3
"""
Check Folder Configuration in Detail

Check which folders are configured and which are missing
"""

import sys
import os
sys.path.append('/Users/frankfilippis/GitHub/DocumentEvaluator')

from server.database import Session
from server.models import Folder, Document
from sqlalchemy import func

def check_folders_detailed():
    """Check folder configuration in detail"""
    
    print("🗂️  Detailed Folder Analysis")
    print("=" * 40)
    
    session = Session()
    
    try:
        # Get all folders from database
        folders = session.query(Folder).all()
        
        print(f"📊 Total Folders in Database: {len(folders)}")
        print()
        
        for folder in folders:
            print(f"Folder ID: {folder.id}")
            print(f"  Path: {folder.folder_path}")
            print(f"  Name: {folder.folder_name}")
            print(f"  Active: {folder.active}")
            print(f"  Created: {folder.created_at}")
            
            # Count documents
            doc_count = session.query(Document).filter(Document.folder_id == folder.id).count()
            print(f"  Documents: {doc_count}")
            
            # Check if path exists
            if os.path.exists(folder.folder_path):
                try:
                    files = [f for f in os.listdir(folder.folder_path) 
                            if f.endswith(('.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx'))]
                    print(f"  Files on disk: {len(files)}")
                    if files:
                        print(f"  Sample files: {files[:3]}")
                except Exception as e:
                    print(f"  Error reading directory: {e}")
            else:
                print(f"  ⚠️  Path does not exist!")
            print()
        
        # Check the specific missing folder
        missing_folder = "/Users/frankfilippis/AI/CAPUS/04 - MODULA DOCUMENTATION/08 VLMs"
        print(f"🔍 Checking Missing Folder:")
        print(f"Path: {missing_folder}")
        
        if os.path.exists(missing_folder):
            try:
                files = [f for f in os.listdir(missing_folder)
                        if f.endswith(('.pdf', '.txt', '.doc', '.docx', '.xls', '.xlsx', '.md'))]
                print(f"✅ Path exists with {len(files)} processable files")
                if files:
                    print(f"Files found:")
                    for file in files:
                        print(f"  - {file}")
            except Exception as e:
                print(f"❌ Error reading directory: {e}")
        else:
            print(f"❌ Path does not exist!")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error: {e}")
        session.close()
        return False

def add_missing_folder():
    """Add the missing folder to the database"""
    
    print(f"\n➕ Adding Missing Folder")
    print("=" * 30)
    
    missing_folder = "/Users/frankfilippis/AI/CAPUS/04 - MODULA DOCUMENTATION/08 VLMs"
    
    # Check if folder exists first
    if not os.path.exists(missing_folder):
        print(f"❌ Cannot add folder - path does not exist: {missing_folder}")
        return False
    
    session = Session()
    
    try:
        # Check if folder already exists in database
        existing = session.query(Folder).filter(Folder.folder_path == missing_folder).first()
        
        if existing:
            print(f"⚠️  Folder already exists in database:")
            print(f"   ID: {existing.id}")
            print(f"   Active: {existing.active}")
            if existing.active == 0:
                print(f"   Making folder active...")
                existing.active = 1
                session.commit()
                print(f"✅ Folder activated!")
            return True
        
        # Add new folder
        new_folder = Folder(
            folder_path=missing_folder,
            folder_name="08 VLMs",
            active=1
        )
        
        session.add(new_folder)
        session.commit()
        
        print(f"✅ Added new folder:")
        print(f"   ID: {new_folder.id}")
        print(f"   Path: {new_folder.folder_path}")
        print(f"   Name: {new_folder.folder_name}")
        print(f"   Active: {new_folder.active}")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"❌ Error adding folder: {e}")
        session.rollback()
        session.close()
        return False

def main():
    """Main function"""
    
    print("🚀 Folder Configuration Check")
    print("=" * 50)
    print("Host: tablemini.local:5432")
    print("Database: doc_eval")
    print()
    
    # Check current folders
    check_ok = check_folders_detailed()
    
    if check_ok:
        # Ask to add missing folder
        print("\n" + "=" * 50)
        print("💡 Would you like to add the missing folder?")
        print("   This will add: /Users/frankfilippis/AI/CAPUS/04 - MODULA DOCUMENTATION/08 VLMs")
        print("   to the database so it gets processed in future runs.")
        
        # For automation, let's add it
        add_ok = add_missing_folder()
        
        if add_ok:
            print("\n✅ Folder configuration updated!")
            print("💡 The folder will be included in the next process-db-folders call.")
        else:
            print("\n⚠️  Could not add the missing folder.")

if __name__ == "__main__":
    main()
