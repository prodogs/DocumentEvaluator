"""
Dynamic Processing Queue Service

This service monitors for available processing slots and automatically processes
waiting documents when slots become available. It works in conjunction with the
status polling service to provide continuous document processing.
"""

import time
import threading
import logging
from typing import List, Dict, Any
from sqlalchemy.sql import func
from models import LlmResponse, Document, Connection, Prompt, Batch
from database import Session

logger = logging.getLogger(__name__)

class DynamicProcessingQueue:
    """Service to automatically process waiting documents when slots become available"""

    def __init__(self, check_interval=5, max_outstanding=30):
        """
        Initialize the dynamic processing queue

        Args:
            check_interval (int): Seconds between availability checks (default: 5)
            max_outstanding (int): Maximum concurrent processing documents (default: 30)
        """
        self.check_interval = check_interval
        self.max_outstanding = max_outstanding
        self.queue_thread = None
        self.stop_queue = False
        self.processing_lock = threading.Lock()

    def start_queue_processing(self):
        """Start the background queue processing thread"""
        if self.queue_thread and self.queue_thread.is_alive():
            logger.warning("Queue processing thread is already running")
            return

        self.stop_queue = False
        self.queue_thread = threading.Thread(target=self._queue_processing_loop, daemon=True)
        self.queue_thread.start()
        logger.info("Dynamic processing queue started")

    def stop_queue_processing(self):
        """Stop the background queue processing thread"""
        self.stop_queue = True
        if self.queue_thread:
            self.queue_thread.join(timeout=5)
        logger.info("Dynamic processing queue stopped")

    def _queue_processing_loop(self):
        """Main queue processing loop that runs in the background"""
        while not self.stop_queue:
            try:
                self._process_available_slots()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in queue processing loop: {e}", exc_info=True)
                time.sleep(self.check_interval)

    def _process_available_slots(self):
        """Check for available slots and process waiting documents"""
        with self.processing_lock:
            session = Session()
            try:
                # Check current outstanding count
                current_outstanding = session.query(LlmResponse).filter(
                    LlmResponse.status == 'P'
                ).count()

                available_slots = self.max_outstanding - current_outstanding

                if available_slots <= 0:
                    logger.debug(f"No available slots: {current_outstanding}/{self.max_outstanding}")
                    return

                logger.info(f"🔄 Available processing slots: {available_slots} (current: {current_outstanding}/{self.max_outstanding})")

                # Find waiting documents (status 'N') from non-paused batches
                waiting_responses = session.query(LlmResponse).join(Document).join(Batch).filter(
                    LlmResponse.status == 'N',
                    Batch.status != 'PA'  # Exclude documents from paused batches
                ).order_by(LlmResponse.id).limit(available_slots).all()

                if not waiting_responses:
                    logger.debug("No waiting documents found")
                    return

                logger.info(f"📋 Found {len(waiting_responses)} waiting documents to process")

                # Process each waiting document
                processed_count = 0
                for llm_response in waiting_responses:
                    try:
                        # Double-check we haven't exceeded the limit
                        current_outstanding = session.query(LlmResponse).filter(
                            LlmResponse.status == 'P'
                        ).count()

                        if current_outstanding >= self.max_outstanding:
                            logger.info(f"Outstanding limit reached during processing: {current_outstanding}/{self.max_outstanding}")
                            break

                        # Process this document
                        if self._process_single_document(session, llm_response):
                            processed_count += 1

                    except Exception as e:
                        logger.error(f"Error processing waiting document {llm_response.id}: {e}", exc_info=True)

                if processed_count > 0:
                    logger.info(f"✅ Successfully started processing {processed_count} waiting documents")

            except Exception as e:
                logger.error(f"Error in _process_available_slots: {e}", exc_info=True)
            finally:
                session.close()

    def _process_single_document(self, session, llm_response: LlmResponse) -> bool:
        """
        Process a single waiting document

        Args:
            session: Database session
            llm_response: LlmResponse object to process

        Returns:
            bool: True if processing started successfully, False otherwise
        """
        try:
            # Get the document
            document = session.query(Document).filter_by(id=llm_response.document_id).first()
            if not document:
                logger.error(f"Document {llm_response.document_id} not found for LLM response {llm_response.id}")
                return False

            # Get the connection
            connection = session.query(Connection).filter_by(id=llm_response.connection_id).first()
            if not connection:
                logger.error(f"Connection {llm_response.connection_id} not found for LLM response {llm_response.id}")
                return False

            # Get the prompt
            prompt = session.query(Prompt).filter_by(id=llm_response.prompt_id).first()
            if not prompt:
                logger.error(f"Prompt {llm_response.prompt_id} not found for LLM response {llm_response.id}")
                return False

            # Update status to processing
            llm_response.status = 'P'
            llm_response.started_processing_at = func.now()
            session.commit()

            logger.info(f"Updated LLM response {llm_response.id} to processing status (N -> P)")

            # Process the document using the existing processing logic
            # We'll call the processing logic in a separate thread to avoid blocking the queue
            # Pass only IDs to avoid SQLAlchemy session issues across threads
            processing_thread = threading.Thread(
                target=self._process_document_async,
                args=(document.filepath, document.filename, connection.id, prompt.id, llm_response.id),
                daemon=True
            )
            processing_thread.start()

            return True

        except Exception as e:
            logger.error(f"Error processing single document {llm_response.id}: {e}", exc_info=True)
            # Reset status back to 'N' on error
            try:
                llm_response.status = 'N'
                llm_response.started_processing_at = None
                session.commit()
            except Exception:
                pass
            return False

    def _process_document_async(self, file_path, filename, connection_id, prompt_id, llm_response_id):
        """
        Process a single document asynchronously

        This method contains the core document processing logic extracted from process_folder.py

        Args:
            file_path (str): Path to the document file
            filename (str): Name of the document file
            connection_id (int): ID of the connection
            prompt_id (int): ID of the prompt
            llm_response_id (int): ID of the LLM response record
        """
        import os
        import json
        import time
        from services.client import rag_client, RequestMethod
        from api.status_polling import polling_service

        session = Session()
        try:
            # Get the LLM response record
            llm_response = session.query(LlmResponse).filter_by(id=llm_response_id).first()
            if not llm_response:
                logger.error(f"LLM response {llm_response_id} not found")
                return

            # Get the connection with provider and model info
            from sqlalchemy import text
            result = session.execute(text("""
                SELECT c.*, p.provider_type, m.display_name as model_name
                FROM connections c
                LEFT JOIN llm_providers p ON c.provider_id = p.id
                LEFT JOIN models m ON c.model_id = m.id
                WHERE c.id = :connection_id
            """), {"connection_id": connection_id})

            connection_row = result.fetchone()
            if not connection_row:
                logger.error(f"Connection {connection_id} not found")
                llm_response.status = 'F'
                llm_response.completed_processing_at = func.now()
                llm_response.error_message = f"Connection {connection_id} not found"
                session.commit()
                return

            # Get the prompt
            prompt = session.query(Prompt).filter_by(id=prompt_id).first()
            if not prompt:
                logger.error(f"Prompt {prompt_id} not found")
                llm_response.status = 'F'
                llm_response.completed_processing_at = func.now()
                llm_response.error_message = f"Prompt {prompt_id} not found"
                session.commit()
                return

            # Get the document and batch for meta_data
            document = session.query(Document).filter_by(id=llm_response.document_id).first()
            batch_meta_data = None
            if document and document.batch_id:
                from models import Batch
                batch = session.query(Batch).filter_by(id=document.batch_id).first()
                if batch and batch.meta_data:
                    batch_meta_data = batch.meta_data
                    logger.info(f"Using batch meta_data: {batch_meta_data}")

            logger.info(f"Processing document: {filename} with Connection: {connection_row.name}, Prompt ID: {prompt.id}")

            # Read the file content
            try:
                with open(file_path, 'rb') as f:
                    file_content_bytes = f.read()

                # Determine MIME type
                file_extension = os.path.splitext(filename)[1].lower()
                if file_extension == '.pdf':
                    mime_type = 'application/pdf'
                elif file_extension in ['.txt', '.md']:
                    mime_type = 'text/plain'
                elif file_extension in ['.doc', '.docx']:
                    mime_type = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
                elif file_extension in ['.xls', '.xlsx']:
                    mime_type = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
                else:
                    mime_type = 'application/octet-stream'

                # Validate file
                if len(file_content_bytes) == 0:
                    raise ValueError(f"File {filename} is empty")

                max_file_size = 50 * 1024 * 1024  # 50MB limit
                if len(file_content_bytes) > max_file_size:
                    raise ValueError(f"File {filename} is too large: {len(file_content_bytes)} bytes")

            except Exception as e:
                error_msg = f"Error reading file {file_path}: {str(e)}"
                llm_response.status = 'F'
                llm_response.completed_processing_at = func.now()
                llm_response.error_message = error_msg
                session.commit()
                logger.error(error_msg)
                return

            # Call RAG service
            try:
                prompts_data = [{'prompt': prompt.prompt_text}]
                llm_provider_data = {
                    'provider_type': connection_row.provider_type,
                    'url': connection_row.base_url,  # RAG API expects 'url' field instead of 'base_url'
                    'model_name': connection_row.model_name or 'default',
                    'api_key': connection_row.api_key,
                    'port_no': connection_row.port_no
                }

                start_time = time.time()

                # Prepare request data
                request_data = {
                    'filename': filename,
                    'prompts': json.dumps(prompts_data),
                    'llm_provider': json.dumps(llm_provider_data)
                }

                # Add meta_data if available
                if batch_meta_data:
                    request_data['meta_data'] = json.dumps(batch_meta_data)

                response = rag_client.client.call_service(
                    service_name="rag_api",
                    endpoint="/analyze_document_with_llm",
                    method=RequestMethod.POST,
                    data=request_data,
                    files={
                        'file': (filename, file_content_bytes, mime_type)
                    },
                    timeout=60
                )

                end_time = time.time()
                response_time_ms = round((end_time - start_time) * 1000, 2)

                if response.success:
                    task_id_from_service = response.data.get('task_id') if response.data else None

                    if task_id_from_service:
                        # Store the service task_id
                        llm_response.task_id = task_id_from_service
                        llm_response.response_text = f"Task initiated with ID: {task_id_from_service}"
                        llm_response.response_time_ms = int(response_time_ms)
                        llm_response.error_message = None

                        # Also store task_id in documents table
                        document = session.query(Document).filter_by(id=llm_response.document_id).first()
                        if document:
                            document.task_id = task_id_from_service

                        session.commit()
                        logger.info(f"Task initiated: {task_id_from_service} for {filename}")

                        # Start polling service if needed
                        if not polling_service.polling_thread or not polling_service.polling_thread.is_alive():
                            polling_service.start_polling()
                            logger.info("Started polling service for task monitoring")
                    else:
                        # No task_id returned
                        llm_response.status = 'F'
                        llm_response.completed_processing_at = func.now()
                        llm_response.response_time_ms = int(response_time_ms)
                        llm_response.error_message = f"No task_id returned: {response.data}"
                        session.commit()
                        logger.error(f"No task_id returned for {filename}")
                else:
                    # Service error
                    error_details = f"Status: {response.status_code}, Error: {response.error_message}"
                    llm_response.status = 'F'
                    llm_response.completed_processing_at = func.now()
                    llm_response.response_time_ms = int(response_time_ms)
                    llm_response.error_message = f"RAG API failed: {error_details}"
                    session.commit()
                    logger.error(f"RAG API failed for {filename}: {error_details}")

            except Exception as e:
                # Processing error
                llm_response.status = 'F'
                llm_response.completed_processing_at = func.now()
                llm_response.error_message = str(e)
                session.commit()
                logger.error(f"Processing failed for {filename}: {e}", exc_info=True)

        except Exception as e:
            logger.error(f"Error in _process_document_async: {e}", exc_info=True)
        finally:
            session.close()

    def get_queue_status(self) -> Dict[str, Any]:
        """Get current queue status information"""
        session = Session()
        try:
            current_outstanding = session.query(LlmResponse).filter(
                LlmResponse.status == 'P'
            ).count()

            waiting_count = session.query(LlmResponse).filter(
                LlmResponse.status == 'N'
            ).count()

            available_slots = self.max_outstanding - current_outstanding

            return {
                'current_outstanding': current_outstanding,
                'max_outstanding': self.max_outstanding,
                'available_slots': available_slots,
                'waiting_documents': waiting_count,
                'queue_running': self.queue_thread and self.queue_thread.is_alive()
            }
        finally:
            session.close()

# Global instance
dynamic_queue = DynamicProcessingQueue()
