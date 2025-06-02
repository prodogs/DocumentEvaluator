"""
Batch Cleanup Service - DEPRECATED

This service has been deprecated because the LlmResponse table has been moved
to the KnowledgeDocuments database. All LLM processing functionality is now
handled in a separate database.

Original functionality:
- Automatic cleanup of stale batches
- Update batch progress based on LLM responses
- Background cleanup processing

Current status: All methods return deprecation messages or no-op
"""

import threading
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, Any

logger = logging.getLogger(__name__)


class BatchCleanupService:
    """DEPRECATED: Service to clean up stale batches - LlmResponse moved to KnowledgeDocuments database"""

    def __init__(self, check_interval=300, stale_threshold_minutes=30):
        """
        Initialize the deprecated batch cleanup service
        
        Args:
            check_interval (int): Seconds between cleanup checks (default: 300 = 5 minutes)
            stale_threshold_minutes (int): Minutes after which empty batches are considered stale (default: 30)
        """
        self.check_interval = check_interval
        self.stale_threshold_minutes = stale_threshold_minutes
        self.cleanup_thread = None
        self.stop_cleanup = False
        
        logger.warning("Batch cleanup service initialized but LLM processing has been moved to KnowledgeDocuments database")

    def start_cleanup_service(self):
        """DEPRECATED: Start cleanup service - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("start_cleanup_service called but LLM processing has been moved to KnowledgeDocuments database")
        # No-op since there's nothing to clean up

    def stop_cleanup_service(self):
        """DEPRECATED: Stop cleanup service - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("stop_cleanup_service called but LLM processing has been moved to KnowledgeDocuments database")
        # No-op since there's nothing to stop

    def _cleanup_loop(self):
        """DEPRECATED: Cleanup loop - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("_cleanup_loop called but LLM processing has been moved to KnowledgeDocuments database")
        # No-op since there's nothing to clean up

    def _cleanup_stale_batches(self):
        """DEPRECATED: Cleanup stale batches - LlmResponse moved to KnowledgeDocuments database"""
        logger.debug("_cleanup_stale_batches called but LLM processing has been moved to KnowledgeDocuments database")
        # No-op since there are no batches to clean up

    def manual_cleanup_all_stale_batches(self) -> Dict[str, Any]:
        """DEPRECATED: Manual cleanup - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("manual_cleanup_all_stale_batches called but LLM processing has been moved to KnowledgeDocuments database")
        
        return {
            'deprecated': True,
            'cleaned_up_batches': 0,
            'message': 'Batch cleanup service moved to KnowledgeDocuments database',
            'reason': 'llm_responses table moved to separate database'
        }

    def get_cleanup_status(self) -> Dict[str, Any]:
        """DEPRECATED: Get cleanup status - LlmResponse moved to KnowledgeDocuments database"""
        logger.debug("get_cleanup_status called but LLM processing has been moved to KnowledgeDocuments database")
        
        return {
            'deprecated': True,
            'is_running': False,
            'last_cleanup': None,
            'stale_threshold_minutes': self.stale_threshold_minutes,
            'check_interval': self.check_interval,
            'message': 'Batch cleanup service moved to KnowledgeDocuments database',
            'reason': 'llm_responses table moved to separate database'
        }

    def cleanup_batch(self, batch_id: int) -> Dict[str, Any]:
        """DEPRECATED: Cleanup specific batch - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning(f"cleanup_batch called for batch {batch_id} but LLM processing has been moved to KnowledgeDocuments database")
        
        return {
            'deprecated': True,
            'batch_id': batch_id,
            'cleaned_up': False,
            'message': 'Batch cleanup service moved to KnowledgeDocuments database',
            'reason': 'llm_responses table moved to separate database'
        }


# Create a singleton instance for backward compatibility
batch_cleanup_service = BatchCleanupService()
