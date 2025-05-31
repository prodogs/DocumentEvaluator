"""
Startup Recovery Service

This service handles recovery of outstanding tasks when the application starts.
It checks for documents with task_ids that are still in processing state and
resumes monitoring them.
"""

import logging
from typing import List, Dict, Any
from database import Session
from models import Document, LlmResponse
from api.status_polling import polling_service
from services.client import rag_client, RequestMethod
from sqlalchemy.sql import func

logger = logging.getLogger(__name__)

class StartupRecoveryService:
    """Service to handle recovery of outstanding tasks on startup"""

    def __init__(self):
        self.recovered_tasks = []
        self.failed_recoveries = []

    def find_outstanding_tasks(self) -> List[Dict[str, Any]]:
        """
        Find all documents and LLM responses that have outstanding task_ids

        Returns:
            List of dictionaries containing task information
        """
        session = Session()
        outstanding_tasks = []

        try:
            # Find all LLM responses that are in processing state with task_ids
            processing_responses = session.query(LlmResponse).filter(
                LlmResponse.status == 'P',
                LlmResponse.task_id.isnot(None)
            ).all()

            logger.info(f"Found {len(processing_responses)} LLM responses in processing state with task_ids")

            for response in processing_responses:
                # Get the associated document
                document = session.query(Document).filter_by(id=response.document_id).first()

                task_info = {
                    'task_id': response.task_id,
                    'document_id': response.document_id,
                    'document_filename': document.filename if document else 'Unknown',
                    'llm_response_id': response.id,
                    'llm_name': response.llm_name,
                    'prompt_id': response.prompt_id,
                    'started_at': response.started_processing_at,
                    'recovery_type': 'processing_with_task_id'
                }
                outstanding_tasks.append(task_info)

            # Find LLM responses with 'N' (Not started) status - these were created but never processed
            not_started_responses = session.query(LlmResponse).filter(
                LlmResponse.status == 'N'
            ).all()

            logger.info(f"Found {len(not_started_responses)} LLM responses in 'N' (not started) state")

            for response in not_started_responses:
                # Get the associated document
                document = session.query(Document).filter_by(id=response.document_id).first()

                task_info = {
                    'task_id': None,  # No task_id yet since processing never started
                    'document_id': response.document_id,
                    'document_filename': document.filename if document else 'Unknown',
                    'llm_response_id': response.id,
                    'llm_name': response.llm_name,
                    'prompt_id': response.prompt_id,
                    'started_at': None,  # Never started
                    'recovery_type': 'not_started',
                    'needs_processing': True
                }
                outstanding_tasks.append(task_info)

            # Also check for documents with task_ids but no corresponding processing LLM responses
            documents_with_tasks = session.query(Document).filter(
                Document.task_id.isnot(None)
            ).all()

            for document in documents_with_tasks:
                # Check if there's already a processing response for this document
                existing_processing = any(
                    task['document_id'] == document.id
                    for task in outstanding_tasks
                )

                if not existing_processing:
                    # This document has a task_id but no processing LLM response
                    # This might indicate an orphaned task
                    task_info = {
                        'task_id': document.task_id,
                        'document_id': document.id,
                        'document_filename': document.filename,
                        'llm_response_id': None,
                        'llm_name': 'Unknown',
                        'prompt_id': None,
                        'started_at': document.created_at,
                        'orphaned': True
                    }
                    outstanding_tasks.append(task_info)

            logger.info(f"Total outstanding tasks found: {len(outstanding_tasks)}")
            return outstanding_tasks

        except Exception as e:
            logger.error(f"Error finding outstanding tasks: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def check_task_status(self, task_id: str) -> Dict[str, Any]:
        """
        Check the status of a specific task with the RAG service

        Args:
            task_id: The task ID to check

        Returns:
            Dictionary containing task status information
        """
        try:
            logger.info(f"Checking status for task: {task_id}")

            # Call the RAG service to get task status
            response = rag_client.client.call_service(
                service_name="rag_api",
                endpoint=f"/analyze_status/{task_id}",
                method=RequestMethod.GET,
                timeout=30
            )

            if response.success and response.data:
                status_info = {
                    'task_id': task_id,
                    'status': response.data.get('status', 'Unknown'),
                    'result': response.data.get('result'),
                    'error': response.data.get('error'),
                    'service_available': True
                }
                logger.info(f"Task {task_id} status: {status_info['status']}")
                return status_info
            elif response.status_code == 404:
                # Task not found - treat as failed
                logger.warning(f"Task {task_id} not found on service (404) - marking as failed")
                return {
                    'task_id': task_id,
                    'status': 'NOT_FOUND',
                    'error': f"Task not found on service - may have expired",
                    'service_available': True
                }
            else:
                logger.warning(f"Failed to get status for task {task_id}: {response.error_message}")
                return {
                    'task_id': task_id,
                    'status': 'Unknown',
                    'error': f"Service error: {response.error_message}",
                    'service_available': False
                }

        except Exception as e:
            logger.error(f"Error checking task status for {task_id}: {e}", exc_info=True)
            return {
                'task_id': task_id,
                'status': 'Error',
                'error': str(e),
                'service_available': False
            }

    def recover_task(self, task_info: Dict[str, Any], status_info: Dict[str, Any]) -> bool:
        """
        Recover a specific task based on its current status

        Args:
            task_info: Information about the task from the database
            status_info: Current status information from the service

        Returns:
            True if recovery was successful, False otherwise
        """
        session = Session()

        try:
            task_id = task_info['task_id']
            service_status = status_info['status']

            logger.info(f"Recovering task {task_id} with status: {service_status}")

            # Get the LLM response record if it exists
            if task_info['llm_response_id']:
                llm_response = session.query(LlmResponse).filter_by(
                    id=task_info['llm_response_id']
                ).first()
            else:
                llm_response = None

            if service_status in ['completed', 'success', 'S']:
                # Task completed successfully
                if llm_response and status_info.get('result'):
                    llm_response.status = 'S'
                    llm_response.response_text = status_info['result']
                    llm_response.completed_processing_at = func.now()
                    session.commit()
                    logger.info(f"Recovered completed task {task_id}")
                    return True

            elif service_status in ['failed', 'error', 'F', 'NOT_FOUND']:
                # Task failed or not found
                if llm_response:
                    llm_response.status = 'F'
                    if service_status == 'NOT_FOUND':
                        llm_response.error_message = 'Task not found on service - may have expired'
                    else:
                        llm_response.error_message = status_info.get('error', 'Task failed during processing')
                    llm_response.completed_processing_at = func.now()
                    session.commit()
                    logger.info(f"Recovered failed task {task_id} (status: {service_status})")
                    return True

            elif service_status in ['processing', 'pending', 'P']:
                # Task still processing - add to polling service
                logger.info(f"Task {task_id} still processing - will continue monitoring")
                return True

            else:
                # Unknown status - mark as failed
                if llm_response:
                    llm_response.status = 'F'
                    llm_response.error_message = f"Unknown task status during recovery: {service_status}"
                    llm_response.completed_processing_at = func.now()
                    session.commit()
                    logger.warning(f"Task {task_id} has unknown status: {service_status}")
                    return True

            return False

        except Exception as e:
            logger.error(f"Error recovering task {task_info['task_id']}: {e}", exc_info=True)
            return False
        finally:
            session.close()

    def run_startup_recovery(self) -> Dict[str, Any]:
        """
        Run the complete startup recovery process

        Returns:
            Dictionary containing recovery results
        """
        logger.info("Starting startup recovery process...")

        # Find all outstanding tasks
        outstanding_tasks = self.find_outstanding_tasks()

        if not outstanding_tasks:
            logger.info("No outstanding tasks found - recovery complete")
            return {
                'total_tasks': 0,
                'recovered_tasks': 0,
                'failed_recoveries': 0,
                'still_processing': 0
            }

        recovered_count = 0
        failed_count = 0
        still_processing_count = 0

        # Check status and recover each task
        for task_info in outstanding_tasks:
            task_id = task_info['task_id']
            recovery_type = task_info.get('recovery_type', 'unknown')

            if recovery_type == 'not_started':
                # Handle 'N' status records - these need to be reset or cleaned up
                logger.info(f"Found not-started task for document {task_info['document_filename']} - resetting to ready state")

                # Reset the LLM response to a clean state for potential reprocessing
                session = Session()
                try:
                    if task_info['llm_response_id']:
                        llm_response = session.query(LlmResponse).filter_by(
                            id=task_info['llm_response_id']
                        ).first()
                        if llm_response:
                            # Keep status as 'N' but ensure it's clean
                            llm_response.task_id = None
                            llm_response.started_processing_at = None
                            llm_response.completed_processing_at = None
                            llm_response.error_message = None
                            llm_response.response_text = None
                            session.commit()
                            logger.info(f"Reset not-started LLM response {task_info['llm_response_id']} to clean state")
                            recovered_count += 1
                        else:
                            logger.warning(f"Could not find LLM response {task_info['llm_response_id']} for reset")
                            failed_count += 1
                    else:
                        logger.warning(f"No LLM response ID for not-started task")
                        failed_count += 1
                except Exception as e:
                    logger.error(f"Error resetting not-started task: {e}")
                    failed_count += 1
                finally:
                    session.close()

                self.recovered_tasks.append(task_info)
                continue

            if not task_id:
                logger.warning(f"Task info missing task_id: {task_info}")
                failed_count += 1
                self.failed_recoveries.append(task_info)
                continue

            # Check current status with the service
            status_info = self.check_task_status(task_id)

            # Attempt recovery
            if self.recover_task(task_info, status_info):
                if status_info['status'] in ['processing', 'pending', 'P']:
                    still_processing_count += 1
                else:
                    recovered_count += 1
                self.recovered_tasks.append(task_info)
            else:
                failed_count += 1
                self.failed_recoveries.append(task_info)

        # Start the polling service if there are still processing tasks
        if still_processing_count > 0:
            if not polling_service.polling_thread or not polling_service.polling_thread.is_alive():
                polling_service.start_polling()
                logger.info(f"Started polling service to monitor {still_processing_count} ongoing tasks")

        recovery_results = {
            'total_tasks': len(outstanding_tasks),
            'recovered_tasks': recovered_count,
            'failed_recoveries': failed_count,
            'still_processing': still_processing_count
        }

        logger.info(f"Startup recovery complete: {recovery_results}")
        return recovery_results

# Global instance
startup_recovery_service = StartupRecoveryService()
