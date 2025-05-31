"""
Batch Cleanup Service

This service handles cleanup of stale batches that are stuck in processing state
but have no actual documents or responses to process.
"""

import logging
import threading
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
from sqlalchemy.sql import func
from models import Batch, Document, LlmResponse
from database import Session

logger = logging.getLogger(__name__)

class BatchCleanupService:
    """Service to automatically clean up stale batches"""

    def __init__(self, check_interval=300, stale_threshold_minutes=30):
        """
        Initialize the batch cleanup service

        Args:
            check_interval (int): Seconds between cleanup checks (default: 300 = 5 minutes)
            stale_threshold_minutes (int): Minutes after which empty batches are considered stale (default: 30)
        """
        self.check_interval = check_interval
        self.stale_threshold_minutes = stale_threshold_minutes
        self.cleanup_thread = None
        self.stop_cleanup = False

    def start_cleanup_service(self):
        """Start the background cleanup thread"""
        if self.cleanup_thread and self.cleanup_thread.is_alive():
            logger.warning("Batch cleanup service is already running")
            return

        self.stop_cleanup = False
        self.cleanup_thread = threading.Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        logger.info("Batch cleanup service started")

    def stop_cleanup_service(self):
        """Stop the background cleanup thread"""
        self.stop_cleanup = True
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5)
        logger.info("Batch cleanup service stopped")

    def _cleanup_loop(self):
        """Main cleanup loop that runs in the background"""
        while not self.stop_cleanup:
            try:
                self._cleanup_stale_batches()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in batch cleanup loop: {e}", exc_info=True)
                time.sleep(self.check_interval)

    def _cleanup_stale_batches(self):
        """Find and clean up stale batches"""
        session = Session()
        try:
            # Find batches that are in processing state but have no documents or responses
            stale_threshold = datetime.now() - timedelta(minutes=self.stale_threshold_minutes)
            
            processing_batches = session.query(Batch).filter(
                Batch.status == 'P',
                Batch.created_at < stale_threshold
            ).all()

            logger.debug(f"Found {len(processing_batches)} processing batches older than {self.stale_threshold_minutes} minutes")

            cleaned_count = 0
            for batch in processing_batches:
                if self._should_cleanup_batch(session, batch):
                    self._cleanup_batch(session, batch)
                    cleaned_count += 1

            if cleaned_count > 0:
                logger.info(f"Cleaned up {cleaned_count} stale batches")

        except Exception as e:
            logger.error(f"Error in _cleanup_stale_batches: {e}", exc_info=True)
        finally:
            session.close()

    def _should_cleanup_batch(self, session, batch: Batch) -> bool:
        """
        Determine if a batch should be cleaned up
        
        Args:
            session: Database session
            batch: Batch to check
            
        Returns:
            bool: True if batch should be cleaned up
        """
        try:
            # Count documents in this batch
            document_count = session.query(Document).filter_by(batch_id=batch.id).count()
            
            # Count responses for documents in this batch
            response_count = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch.id
            ).count()
            
            # Batch should be cleaned up if:
            # 1. It has no documents AND no responses
            # 2. OR it has been processing for too long with no progress
            
            if document_count == 0 and response_count == 0:
                logger.debug(f"Batch {batch.id} (#{batch.batch_number}) has no documents or responses - marking for cleanup")
                return True
                
            # Check if batch has been stuck for too long
            if batch.started_at:
                processing_time = datetime.now() - batch.started_at
                if processing_time.total_seconds() > (self.stale_threshold_minutes * 60 * 2):  # 2x threshold
                    # Check if there's any recent activity
                    recent_responses = session.query(LlmResponse).join(Document).filter(
                        Document.batch_id == batch.id,
                        LlmResponse.completed_processing_at > (datetime.now() - timedelta(minutes=self.stale_threshold_minutes))
                    ).count()
                    
                    if recent_responses == 0:
                        logger.debug(f"Batch {batch.id} (#{batch.batch_number}) has been stuck for {processing_time} with no recent activity")
                        return True
            
            return False
            
        except Exception as e:
            logger.error(f"Error checking if batch {batch.id} should be cleaned up: {e}")
            return False

    def _cleanup_batch(self, session, batch: Batch):
        """
        Clean up a stale batch by marking it as completed
        
        Args:
            session: Database session
            batch: Batch to clean up
        """
        try:
            # Update batch status to completed
            batch.status = 'C'  # Completed
            batch.completed_at = func.now()
            
            # Update progress counters
            document_count = session.query(Document).filter_by(batch_id=batch.id).count()
            completed_responses = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch.id,
                LlmResponse.status.in_(['S', 'F'])
            ).count()
            
            batch.total_documents = document_count
            batch.processed_documents = completed_responses
            
            session.commit()
            
            logger.info(f"Cleaned up stale batch {batch.id} (#{batch.batch_number} - '{batch.batch_name}')")
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error cleaning up batch {batch.id}: {e}")

    def manual_cleanup_all_stale_batches(self) -> Dict[str, Any]:
        """
        Manually trigger cleanup of all stale batches
        
        Returns:
            Dict with cleanup results
        """
        session = Session()
        try:
            # Find all processing batches
            processing_batches = session.query(Batch).filter(Batch.status == 'P').all()
            
            cleaned_batches = []
            for batch in processing_batches:
                if self._should_cleanup_batch(session, batch):
                    self._cleanup_batch(session, batch)
                    cleaned_batches.append({
                        'id': batch.id,
                        'batch_number': batch.batch_number,
                        'batch_name': batch.batch_name
                    })
            
            return {
                'success': True,
                'cleaned_count': len(cleaned_batches),
                'cleaned_batches': cleaned_batches
            }
            
        except Exception as e:
            logger.error(f"Error in manual cleanup: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }
        finally:
            session.close()

    def get_cleanup_status(self) -> Dict[str, Any]:
        """Get current cleanup service status"""
        return {
            'running': self.cleanup_thread and self.cleanup_thread.is_alive(),
            'check_interval': self.check_interval,
            'stale_threshold_minutes': self.stale_threshold_minutes
        }

# Global instance
batch_cleanup_service = BatchCleanupService()
