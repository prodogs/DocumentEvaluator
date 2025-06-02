"""
Dynamic Processing Queue Service - DEPRECATED

This service has been deprecated because the LlmResponse table has been moved
to the KnowledgeDocuments database. All LLM processing functionality is now
handled in a separate database.

Original functionality:
- Automatic processing of waiting documents when slots become available
- Configurable concurrency limits
- Background queue processing

Current status: All methods return deprecation messages or no-op
"""

import time
import threading
import logging
from typing import Dict, Any

logger = logging.getLogger(__name__)


class DynamicProcessingQueue:
    """DEPRECATED: Dynamic queue for processing LLM responses - LlmResponse moved to KnowledgeDocuments database"""

    def __init__(self, check_interval=5, max_outstanding=30):
        """
        Initialize the deprecated dynamic processing queue
        
        Args:
            check_interval (int): Seconds between availability checks (default: 5)
            max_outstanding (int): Maximum concurrent processing documents (default: 30)
        """
        self.check_interval = check_interval
        self.max_outstanding = max_outstanding
        self.queue_thread = None
        self.stop_queue = False
        self.processing_lock = threading.Lock()
        
        logger.warning("Dynamic processing queue initialized but LLM processing has been moved to KnowledgeDocuments database")

    def start_queue_processing(self):
        """DEPRECATED: Start queue processing - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("start_queue_processing called but LLM processing has been moved to KnowledgeDocuments database")
        # No-op since there's nothing to process

    def stop_queue_processing(self):
        """DEPRECATED: Stop queue processing - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("stop_queue_processing called but LLM processing has been moved to KnowledgeDocuments database")
        # No-op since there's nothing to stop

    def _queue_processing_loop(self):
        """DEPRECATED: Queue processing loop - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("_queue_processing_loop called but LLM processing has been moved to KnowledgeDocuments database")
        # No-op since there's nothing to process

    def _process_waiting_documents(self):
        """DEPRECATED: Process waiting documents - LlmResponse moved to KnowledgeDocuments database"""
        logger.debug("_process_waiting_documents called but LLM processing has been moved to KnowledgeDocuments database")
        # No-op since there are no documents to process

    def _process_single_document(self, session, llm_response) -> bool:
        """DEPRECATED: Process single document - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("_process_single_document called but LLM processing has been moved to KnowledgeDocuments database")
        return False  # Cannot process documents in deprecated service

    def _process_document_async(self, filename, connection_id, prompt_id, llm_response_id):
        """DEPRECATED: Process document async - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning(f"_process_document_async called for {filename} but LLM processing has been moved to KnowledgeDocuments database")
        # No-op since there's nothing to process

    def get_queue_status(self) -> Dict[str, Any]:
        """DEPRECATED: Get queue status - LlmResponse moved to KnowledgeDocuments database"""
        logger.debug("get_queue_status called but LLM processing has been moved to KnowledgeDocuments database")
        
        return {
            'deprecated': True,
            'is_running': False,
            'current_outstanding': 0,
            'waiting_count': 0,
            'available_slots': 0,
            'max_outstanding': self.max_outstanding,
            'check_interval': self.check_interval,
            'message': 'Dynamic processing queue service moved to KnowledgeDocuments database',
            'reason': 'llm_responses table moved to separate database'
        }

    def force_process_waiting(self) -> Dict[str, Any]:
        """DEPRECATED: Force process waiting - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("force_process_waiting called but LLM processing has been moved to KnowledgeDocuments database")
        
        return {
            'deprecated': True,
            'processed': 0,
            'message': 'Force process waiting service moved to KnowledgeDocuments database',
            'reason': 'llm_responses table moved to separate database'
        }


# Create a singleton instance for backward compatibility
dynamic_queue = DynamicProcessingQueue()
