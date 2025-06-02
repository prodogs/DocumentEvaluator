"""
Batch Archive Service - DEPRECATED

This service has been deprecated because the LlmResponse table has been moved
to the KnowledgeDocuments database. All LLM processing functionality is now
handled in a separate database.

Original functionality:
- Archive batches with all associated data
- Delete batches from main tables after archiving
- Retrieve archived batch data
- List archived batches

Current status: All methods return deprecation messages
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)


class BatchArchiveService:
    """DEPRECATED: Service for archiving batches - LlmResponse moved to KnowledgeDocuments database"""

    def __init__(self):
        logger.warning("BatchArchiveService initialized but LLM processing has been moved to KnowledgeDocuments database")

    def archive_and_delete_batch(self, batch_id: int, archived_by: Optional[str] = None, 
                                archive_reason: Optional[str] = None) -> Dict[str, Any]:
        """DEPRECATED: Archive and delete batch - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning(f"archive_and_delete_batch called for batch {batch_id} but LLM processing has been moved to KnowledgeDocuments database")
        
        return {
            'success': False,
            'deprecated': True,
            'batch_id': batch_id,
            'archive_id': None,
            'message': 'Batch archive service moved to KnowledgeDocuments database',
            'reason': 'llm_responses table moved to separate database'
        }

    def get_archived_batch(self, archive_id: int) -> Optional[Dict[str, Any]]:
        """DEPRECATED: Get archived batch - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning(f"get_archived_batch called for archive {archive_id} but LLM processing has been moved to KnowledgeDocuments database")
        
        return {
            'deprecated': True,
            'archive_id': archive_id,
            'message': 'Archived batch retrieval service moved to KnowledgeDocuments database',
            'reason': 'llm_responses table moved to separate database'
        }

    def list_archived_batches(self, limit: int = 50, offset: int = 0) -> Dict[str, Any]:
        """DEPRECATED: List archived batches - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("list_archived_batches called but LLM processing has been moved to KnowledgeDocuments database")
        
        return {
            'deprecated': True,
            'archives': [],
            'total_count': 0,
            'limit': limit,
            'offset': offset,
            'message': 'Archived batch listing service moved to KnowledgeDocuments database',
            'reason': 'llm_responses table moved to separate database'
        }

    def delete_archived_batch(self, archive_id: int) -> Dict[str, Any]:
        """DEPRECATED: Delete archived batch - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning(f"delete_archived_batch called for archive {archive_id} but LLM processing has been moved to KnowledgeDocuments database")
        
        return {
            'success': False,
            'deprecated': True,
            'archive_id': archive_id,
            'message': 'Archived batch deletion service moved to KnowledgeDocuments database',
            'reason': 'llm_responses table moved to separate database'
        }

    def _serialize_batch(self, batch) -> Dict[str, Any]:
        """DEPRECATED: Serialize batch - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("_serialize_batch called but LLM processing has been moved to KnowledgeDocuments database")
        return {}

    def _serialize_document(self, document) -> Dict[str, Any]:
        """DEPRECATED: Serialize document - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("_serialize_document called but LLM processing has been moved to KnowledgeDocuments database")
        return {}

    def _serialize_llm_response(self, response) -> Dict[str, Any]:
        """DEPRECATED: Serialize LLM response - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("_serialize_llm_response called but LLM processing has been moved to KnowledgeDocuments database")
        return {}

    def _count_response_statuses(self, responses: List) -> Dict[str, int]:
        """DEPRECATED: Count response statuses - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("_count_response_statuses called but LLM processing has been moved to KnowledgeDocuments database")
        return {}


# Create a singleton instance for backward compatibility
batch_archive_service = BatchArchiveService()
