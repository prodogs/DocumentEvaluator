import time
import threading
import requests
import json
import logging
from datetime import datetime, timedelta
from sqlalchemy.sql import func
from server.models import LlmResponse
from server.database import Session
from server.services.client import rag_client

logger = logging.getLogger(__name__)

class StatusPollingService:
    """Service to poll the port 7001 service for task status updates"""

    def __init__(self, poll_interval=10, max_poll_duration=3600, rag_api_base_url="http://localhost:7001"):
        """
        Initialize the status polling service

        Args:
            poll_interval (int): Seconds between polls (default: 10)
            max_poll_duration (int): Maximum time to poll a task in seconds (default: 3600 = 1 hour)
            rag_api_base_url (str): Base URL for the RAG API service
        """
        self.poll_interval = poll_interval
        self.max_poll_duration = max_poll_duration
        self.rag_api_base_url = rag_api_base_url
        self.polling_thread = None
        self.stop_polling = False

    def start_polling(self):
        """Start the background polling thread"""
        if self.polling_thread and self.polling_thread.is_alive():
            logger.warning("Polling thread is already running")
            return

        self.stop_polling = False
        self.polling_thread = threading.Thread(target=self._polling_loop, daemon=True)
        self.polling_thread.start()
        logger.info("Status polling service started")

    def stop_polling_service(self):
        """Stop the background polling thread"""
        self.stop_polling = True
        if self.polling_thread:
            self.polling_thread.join(timeout=5)
        logger.info("Status polling service stopped")

    def _polling_loop(self):
        """Main polling loop that runs in the background"""
        while not self.stop_polling:
            try:
                self._poll_pending_tasks()
                time.sleep(self.poll_interval)
            except Exception as e:
                logger.error(f"Error in polling loop: {e}", exc_info=True)
                time.sleep(self.poll_interval)

    def _poll_pending_tasks(self):
        """Poll all pending tasks and update their status"""
        session = Session()
        try:
            # Get all LLM responses that are in 'P' (Processing) status and have a task_id
            pending_responses = session.query(LlmResponse).filter(
                LlmResponse.status == 'P',
                LlmResponse.task_id.isnot(None),
                LlmResponse.task_id != ''
            ).all()

            logger.debug(f"Found {len(pending_responses)} pending tasks to poll")

            for llm_response in pending_responses:
                try:
                    # Check if task has been processing too long
                    if self._is_task_expired(llm_response):
                        self._mark_task_as_timeout(session, llm_response)
                        continue

                    # Poll the status from port 7001 service
                    status_result = self._poll_task_status(llm_response.task_id)

                    if status_result:
                        self._update_task_status(session, llm_response, status_result)

                except Exception as e:
                    logger.error(f"Error polling task {llm_response.task_id}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in _poll_pending_tasks: {e}", exc_info=True)
        finally:
            session.close()

    def _poll_task_status(self, task_id):
        """
        Poll the status of a specific task from the port 7001 service

        Args:
            task_id (str): The task ID to poll

        Returns:
            dict: Status response from the service, or None if error
        """
        try:
            # Use the new service client for better error handling and retry logic
            response = rag_client.get_analysis_status(task_id)

            if response.success:
                return response.data
            elif response.status_code == 404:
                logger.warning(f"Task {task_id} not found on service")
                return {"status": "NOT_FOUND", "task_id": task_id, "message": "Task not found"}
            else:
                logger.error(f"Error polling task {task_id}: Status {response.status_code}, Error: {response.error_message}")
                return None

        except Exception as e:
            logger.error(f"Unexpected error polling task {task_id}: {e}")
            return None

    def _update_task_status(self, session, llm_response, status_result):
        """
        Update the LLM response record based on the status result

        Args:
            session: Database session
            llm_response: LlmResponse object to update
            status_result: Status response from the service
        """
        task_id = llm_response.task_id
        status = status_result.get('status', '').upper()

        logger.debug(f"Updating task {task_id} with status: {status}")

        if status in ['COMPLETED', 'SUCCESS']:
            # Task completed successfully
            self._handle_completed_task(session, llm_response, status_result)

        elif status in ['FAILED', 'ERROR']:
            # Task failed
            self._handle_failed_task(session, llm_response, status_result)

        elif status in ['NOT_FOUND']:
            # Task not found on service
            self._handle_not_found_task(session, llm_response, status_result)

        elif status in ['PROCESSING', 'PENDING', 'STARTED']:
            # Task still processing - no update needed, just log
            logger.debug(f"Task {task_id} still processing")

        else:
            logger.warning(f"Unknown status '{status}' for task {task_id}")

    def _handle_completed_task(self, session, llm_response, status_result):
        """Handle a successfully completed task"""
        try:
            # Extract results from the response
            results = status_result.get('results', [])
            scoring_result = status_result.get('scoring_result', {})
            processing_strategies = status_result.get('processing_strategies', {})

            # Store the complete response data (including scores and processing strategies)
            response_json = status_result

            # Extract overall score (0-100 suitability score)
            overall_score = None
            if scoring_result and 'overall_score' in scoring_result:
                overall_score = scoring_result.get('overall_score')
                # Ensure it's a valid number
                try:
                    overall_score = float(overall_score) if overall_score is not None else None
                except (ValueError, TypeError):
                    overall_score = None

            # Create formatted response text including score information
            response_text = ""

            # Add score information at the top if available
            if scoring_result:
                response_text += "=== SCORING RESULTS ===\n"
                if overall_score is not None:
                    response_text += f"Overall Suitability Score: {overall_score}/100\n"

                confidence = scoring_result.get('confidence')
                if confidence is not None:
                    response_text += f"Confidence: {confidence}\n"

                provider_name = scoring_result.get('provider_name')
                if provider_name:
                    response_text += f"Provider: {provider_name}\n"

                # Add subscores if available
                subscores = scoring_result.get('subscores', {})
                if subscores:
                    response_text += "\nSubscores:\n"
                    for subscore_name, subscore_data in subscores.items():
                        if isinstance(subscore_data, dict):
                            score = subscore_data.get('score', 'N/A')
                            comment = subscore_data.get('comment', '')
                            response_text += f"  {subscore_name}: {score}"
                            if comment:
                                response_text += f" - {comment}"
                            response_text += "\n"

                # Add improvement recommendations if available
                recommendations = scoring_result.get('improvement_recommendations', [])
                if recommendations:
                    response_text += "\nImprovement Recommendations:\n"
                    for i, rec in enumerate(recommendations, 1):
                        response_text += f"  {i}. {rec}\n"

                response_text += "\n" + "="*50 + "\n\n"

            # Add prompt results
            if results:
                response_text += "=== PROMPT RESULTS ===\n"
                for i, result in enumerate(results):
                    prompt = result.get('prompt', 'Unknown prompt')
                    response = result.get('response', 'No response')
                    result_status = result.get('status', 'Unknown')

                    response_text += f"Prompt {i+1}: {prompt}\n"
                    response_text += f"Status: {result_status}\n"
                    response_text += f"Response: {response}\n"

                    if result.get('error_message'):
                        response_text += f"Error: {result['error_message']}\n"

                    response_text += "\n" + "="*50 + "\n\n"
            else:
                if not scoring_result:  # Only show this if we don't have scoring results
                    response_text = status_result.get('message', 'Task completed successfully')

            # Calculate end-to-end response time
            end_to_end_time_ms = self._calculate_end_to_end_time(llm_response)

            # Update the LLM response record
            llm_response.status = 'S'  # Success
            llm_response.completed_processing_at = func.now()
            llm_response.response_text = response_text
            llm_response.response_json = json.dumps(response_json)
            llm_response.error_message = None
            llm_response.overall_score = overall_score  # Store the suitability score (0-100)

            # Update response_time_ms with end-to-end time (overwriting the initial submission time)
            if end_to_end_time_ms is not None:
                llm_response.response_time_ms = end_to_end_time_ms

            session.commit()
            logger.info(f"Task {llm_response.task_id} completed successfully in {end_to_end_time_ms}ms (end-to-end)")

            # Update batch progress to check if batch is complete
            self._update_batch_progress_for_response(llm_response)

            # Trigger dynamic queue to process waiting documents
            self._trigger_dynamic_queue()

        except Exception as e:
            logger.error(f"Error handling completed task {llm_response.task_id}: {e}", exc_info=True)

    def _handle_failed_task(self, session, llm_response, status_result):
        """Handle a failed task"""
        try:
            error_message = status_result.get('error_message') or status_result.get('message', 'Task failed')

            # Calculate end-to-end response time
            end_to_end_time_ms = self._calculate_end_to_end_time(llm_response)

            llm_response.status = 'F'  # Failure
            llm_response.completed_processing_at = func.now()
            llm_response.error_message = error_message
            llm_response.response_json = json.dumps(status_result)

            # Update response_time_ms with end-to-end time (overwriting the initial submission time)
            if end_to_end_time_ms is not None:
                llm_response.response_time_ms = end_to_end_time_ms

            session.commit()
            logger.info(f"Task {llm_response.task_id} failed: {error_message} (end-to-end time: {end_to_end_time_ms}ms)")

            # Update batch progress to check if batch is complete
            self._update_batch_progress_for_response(llm_response)

            # Trigger dynamic queue to process waiting documents
            self._trigger_dynamic_queue()

        except Exception as e:
            logger.error(f"Error handling failed task {llm_response.task_id}: {e}", exc_info=True)

    def _handle_not_found_task(self, session, llm_response, status_result):
        """Handle a task that was not found on the service"""
        try:
            llm_response.status = 'F'  # Failure
            llm_response.completed_processing_at = func.now()
            llm_response.error_message = "Task not found on service - may have expired"
            llm_response.response_json = json.dumps(status_result)

            session.commit()
            logger.warning(f"Task {llm_response.task_id} not found on service")

            # Update batch progress to check if batch is complete
            self._update_batch_progress_for_response(llm_response)

        except Exception as e:
            logger.error(f"Error handling not found task {llm_response.task_id}: {e}", exc_info=True)

    def _calculate_end_to_end_time(self, llm_response):
        """
        Calculate the end-to-end response time from when the task was started
        until now (when it's completed/failed)

        Args:
            llm_response: LlmResponse object with started_processing_at timestamp

        Returns:
            int: End-to-end time in milliseconds, or None if calculation not possible
        """
        try:
            if not llm_response.started_processing_at:
                logger.warning(f"No started_processing_at timestamp for task {llm_response.task_id}")
                return None

            # Calculate time difference from start to now
            start_time = llm_response.started_processing_at
            end_time = datetime.utcnow()

            # Calculate difference in milliseconds
            time_diff = end_time - start_time
            end_to_end_ms = int(time_diff.total_seconds() * 1000)

            logger.debug(f"Task {llm_response.task_id} end-to-end time: {end_to_end_ms}ms")
            return end_to_end_ms

        except Exception as e:
            logger.error(f"Error calculating end-to-end time for task {llm_response.task_id}: {e}")
            return None

    def _is_task_expired(self, llm_response):
        """Check if a task has been processing for too long"""
        if not llm_response.started_processing_at:
            return False

        elapsed_time = datetime.utcnow() - llm_response.started_processing_at
        return elapsed_time.total_seconds() > self.max_poll_duration

    def _mark_task_as_timeout(self, session, llm_response):
        """Mark a task as timed out"""
        try:
            # Calculate end-to-end response time for timeout
            end_to_end_time_ms = self._calculate_end_to_end_time(llm_response)

            llm_response.status = 'F'  # Failure
            llm_response.completed_processing_at = func.now()
            llm_response.error_message = f"Task timed out after {self.max_poll_duration} seconds"

            # Update response_time_ms with end-to-end time (overwriting the initial submission time)
            if end_to_end_time_ms is not None:
                llm_response.response_time_ms = end_to_end_time_ms

            session.commit()
            logger.warning(f"Task {llm_response.task_id} timed out (end-to-end time: {end_to_end_time_ms}ms)")

            # Update batch progress to check if batch is complete
            self._update_batch_progress_for_response(llm_response)

            # Trigger dynamic queue to process waiting documents
            self._trigger_dynamic_queue()

        except Exception as e:
            logger.error(f"Error marking task {llm_response.task_id} as timeout: {e}", exc_info=True)

    def _trigger_dynamic_queue(self):
        """Trigger the dynamic processing queue to check for waiting documents"""
        try:
            # Import here to avoid circular imports
            from server.services.dynamic_processing_queue import dynamic_queue

            # Start the queue if it's not running
            if not dynamic_queue.queue_thread or not dynamic_queue.queue_thread.is_alive():
                dynamic_queue.start_queue_processing()
                logger.info("Started dynamic processing queue")
            else:
                logger.debug("Dynamic processing queue already running")

        except Exception as e:
            logger.error(f"Error triggering dynamic queue: {e}", exc_info=True)

    def _update_batch_progress_for_response(self, llm_response):
        """Update batch progress when an LLM response is completed/failed"""
        try:
            # Import here to avoid circular imports
            from server.services.batch_service import BatchService
            from server.models import Document

            # Get the document to find the batch_id
            session = Session()
            try:
                document = session.query(Document).filter_by(id=llm_response.document_id).first()
                if document and document.batch_id:
                    batch_service = BatchService()
                    batch_service.update_batch_progress(document.batch_id)
                    logger.debug(f"Updated batch progress for batch {document.batch_id}")
                else:
                    logger.debug(f"No batch_id found for document {llm_response.document_id}")
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error updating batch progress for response {llm_response.id}: {e}", exc_info=True)


# Global instance of the polling service
polling_service = StatusPollingService()
