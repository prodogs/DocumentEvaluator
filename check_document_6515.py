#!/usr/bin/env python3
"""
Check document 6515 details
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import Document
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def check_document():
    """Check document 6515"""
    session = Session()
    try:
        doc = session.query(Document).filter_by(id=6515).first()
        if doc:
            logger.info(f"✅ Document 6515 found:")
            logger.info(f"   Filename: {doc.filename}")
            logger.info(f"   Filepath: {doc.filepath}")
            logger.info(f"   Folder ID: {doc.folder_id}")
            logger.info(f"   Batch ID: {doc.batch_id}")
        else:
            logger.error("❌ Document 6515 not found")
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    check_document()