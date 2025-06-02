#!/usr/bin/env python3
"""
Preprocess folder 3 to add documents to the database
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

import requests
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def preprocess_folder():
    """Preprocess folder 3 using the API"""
    try:
        # Call the folder preprocessing API with both folder_path and folder_name
        response = requests.post(
            "http://localhost:5001/api/folders/preprocess",
            json={
                "folder_path": "/Users/frankfilippis/AI/CAPUS/04 - MODULA DOCUMENTATION/F500",
                "folder_name": "F500"
            },
            headers={"Content-Type": "application/json"}
        )
        
        if response.status_code == 200:
            data = response.json()
            logger.info("✅ Folder preprocessing completed successfully")
            logger.info(f"   Response: {data}")
        else:
            logger.error(f"❌ Folder preprocessing failed: {response.status_code}")
            logger.error(f"   Response: {response.text}")
    
    except Exception as e:
        logger.error(f"❌ Error preprocessing folder: {e}")

if __name__ == "__main__":
    preprocess_folder()