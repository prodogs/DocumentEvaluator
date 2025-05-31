#!/usr/bin/env python3
"""
Check folder status in database
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import Folder

def check_folder_status():
    """Check folder status in database"""
    session = Session()
    try:
        folder = session.query(Folder).filter(Folder.id == 1).first()
        if folder:
            print(f'Folder ID: {folder.id}')
            print(f'Name: {folder.folder_name}')
            print(f'Path: {folder.folder_path}')
            print(f'Active: {folder.active}')
            print(f'Status: {folder.status}')
            print(f'Has status attr: {hasattr(folder, "status")}')
            print(f'Status type: {type(folder.status)}')
            print(f'Created at: {folder.created_at}')
        else:
            print('Folder not found')
    finally:
        session.close()

if __name__ == "__main__":
    check_folder_status()
