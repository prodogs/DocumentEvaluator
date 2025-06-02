"""
Startup Recovery Service - DEPRECATED

This service has been deprecated because the LlmResponse table has been moved
to the KnowledgeDocuments database. All LLM processing functionality is now
handled in a separate database.

Original functionality:
- Recovery of outstanding tasks on application startup
- Cleanup of orphaned processing states
- Task status polling and recovery

Current status: All methods return deprecation messages
"""

import logging
from typing import List, Dict, Any

logger = logging.getLogger(__name__)


class StartupRecoveryService:
    """DEPRECATED: Service to handle recovery of outstanding tasks - LlmResponse moved to KnowledgeDocuments database"""

    def __init__(self):
        self.recovered_tasks = []
        self.failed_recoveries = []
        logger.warning("StartupRecoveryService initialized but LLM processing has been moved to KnowledgeDocuments database")

    def find_outstanding_tasks(self) -> List[Dict[str, Any]]:
        """DEPRECATED: Find outstanding tasks - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("find_outstanding_tasks called but LLM processing has been moved to KnowledgeDocuments database")
        return []  # Return empty list since no tasks to recover

    def check_task_status(self, task_id: str) -> Dict[str, Any]:
        """DEPRECATED: Check task status - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning(f"check_task_status called for task {task_id} but LLM processing has been moved to KnowledgeDocuments database")
        return {
            'task_id': task_id,
            'status': 'SERVICE_MOVED',
            'error': 'LLM processing service moved to KnowledgeDocuments database',
            'service_available': False,
            'deprecated': True
        }

    def recover_task(self, task_info: Dict[str, Any], status_info: Dict[str, Any]) -> bool:
        """DEPRECATED: Recover task - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning(f"recover_task called but LLM processing has been moved to KnowledgeDocuments database")
        return False  # Cannot recover tasks in deprecated service

    def run_startup_recovery(self) -> Dict[str, Any]:
        """DEPRECATED: Run startup recovery - LlmResponse moved to KnowledgeDocuments database"""
        logger.warning("run_startup_recovery called but LLM processing has been moved to KnowledgeDocuments database")
        
        return {
            'success': True,  # Success in the sense that no recovery is needed
            'deprecated': True,
            'total_tasks_found': 0,
            'successfully_recovered': 0,
            'failed_recoveries': 0,
            'not_started_tasks_reset': 0,
            'message': 'Startup recovery skipped - LLM processing moved to KnowledgeDocuments database',
            'reason': 'llm_responses table moved to separate database'
        }


# Create a singleton instance for backward compatibility
startup_recovery_service = StartupRecoveryService()
