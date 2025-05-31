#!/usr/bin/env python3
"""
Test folder API response
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import Folder

def test_folder_api_logic():
    """Test the exact logic used in the API"""
    session = Session()
    try:
        folders = session.query(Folder).all()
        
        folder_list = []
        for folder in folders:
            print(f"Processing folder {folder.id}:")
            print(f"  folder.status = {folder.status}")
            print(f"  getattr(folder, 'status', 'NOT_PROCESSED') = {getattr(folder, 'status', 'NOT_PROCESSED')}")
            print(f"  hasattr(folder, 'status') = {hasattr(folder, 'status')}")
            
            folder_data = {
                'id': folder.id,
                'folder_path': folder.folder_path,
                'folder_name': folder.folder_name,
                'active': bool(folder.active),
                'status': getattr(folder, 'status', 'NOT_PROCESSED'),
                'created_at': folder.created_at.isoformat() if folder.created_at else None
            }
            folder_list.append(folder_data)
            print(f"  Final folder_data: {folder_data}")
            print()
        
        print(f"Final folder_list: {folder_list}")
        
    finally:
        session.close()

if __name__ == "__main__":
    test_folder_api_logic()
