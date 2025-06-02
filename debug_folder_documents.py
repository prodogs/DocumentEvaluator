#!/usr/bin/env python3
"""
Debug script to check folder documents and batch assignments
"""

import sys
import os
sys.path.append(os.path.join(os.path.dirname(__file__), 'server'))

from database import Session
from models import Folder, Document, Batch
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def debug_folder_documents():
    """Check folder documents and their batch assignments"""
    session = Session()
    try:
        # Get folder 3
        folder = session.query(Folder).filter_by(id=3).first()
        if not folder:
            logger.error("❌ Folder 3 not found")
            return
        
        logger.info(f"📁 Folder 3: {folder.folder_name} ({folder.folder_path})")
        logger.info(f"   Active: {folder.active}")
        
        # Get all documents in folder 3
        all_docs = session.query(Document).filter_by(folder_id=3).all()
        logger.info(f"📄 Total documents in folder 3: {len(all_docs)}")
        
        if all_docs:
            # Group by batch assignment
            unassigned = [d for d in all_docs if d.batch_id is None]
            assigned = [d for d in all_docs if d.batch_id is not None]
            
            logger.info(f"   📋 Unassigned documents: {len(unassigned)}")
            logger.info(f"   📦 Assigned documents: {len(assigned)}")
            
            # Show some sample documents
            logger.info("\n📄 Sample documents:")
            for i, doc in enumerate(all_docs[:5]):
                logger.info(f"   {i+1}. {doc.filename} (ID: {doc.id}, Batch: {doc.batch_id})")
            
            if len(all_docs) > 5:
                logger.info(f"   ... and {len(all_docs) - 5} more documents")
            
            # Show batch assignments
            if assigned:
                batch_counts = {}
                for doc in assigned:
                    batch_counts[doc.batch_id] = batch_counts.get(doc.batch_id, 0) + 1
                
                logger.info("\n📦 Documents assigned to batches:")
                for batch_id, count in batch_counts.items():
                    batch = session.query(Batch).filter_by(id=batch_id).first()
                    batch_name = batch.batch_name if batch else "Unknown"
                    logger.info(f"   Batch {batch_id} ({batch_name}): {count} documents")
        
        else:
            logger.warning("⚠️ No documents found in folder 3")
            
        # Check recent batches
        logger.info("\n📦 Recent batches:")
        recent_batches = session.query(Batch).order_by(Batch.id.desc()).limit(5).all()
        for batch in recent_batches:
            doc_count = session.query(Document).filter_by(batch_id=batch.id).count()
            logger.info(f"   Batch {batch.id} ({batch.batch_name}): {batch.status}, {doc_count} docs")
        
    except Exception as e:
        logger.error(f"❌ Error: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    debug_folder_documents()