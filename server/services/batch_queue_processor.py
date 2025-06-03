"""
Batch Queue Processor

This service processes batches and their documents through BatchService coordination.
It monitors for ready batches, processes documents, and reports results back.
"""

import time
import json
import logging
import requests
import threading
from datetime import datetime
from typing import Dict, Any, Optional, List
from services.batch_service import batch_service

logger = logging.getLogger(__name__)


class BatchQueueProcessor:
    """Process batches and their documents through BatchService coordination"""
    
    def __init__(self, check_interval=5, max_concurrent=3):
        self.check_interval = check_interval
        self.max_concurrent = max_concurrent
        self.is_running = False
        self.processing_thread = None
        self.active_tasks = {}  # task_id -> document info
        self.stats = {
            'processed': 0,
            'failed': 0,
            'started_at': None,
            'last_activity': None
        }
        
        # RAG API configuration
        self.rag_api_url = "http://localhost:7001"
        
    def start(self):
        """Start the queue processor"""
        if self.is_running:
            logger.warning("Queue processor is already running")
            return
            
        self.is_running = True
        self.stats['started_at'] = datetime.now()
        
        # Recover any PROCESSING documents on startup
        self._recover_processing_documents()
        
        self.processing_thread = threading.Thread(target=self._process_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("BatchQueueProcessor started - using BatchService coordination")
    
    def _recover_processing_documents(self):
        """Recover documents that have a task_id but are still in PROCESSING status"""
        try:
            import psycopg2
            
            # Connect to KnowledgeDocuments database for llm_responses
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Find llm_responses with task_id that are still in PROCESSING status
            kb_cursor.execute("""
                SELECT id as response_id, task_id, document_id, batch_id
                FROM llm_responses
                WHERE status = 'PROCESSING' 
                AND task_id IS NOT NULL
                AND task_id != ''
            """)
            processing_docs = kb_cursor.fetchall()
            
            logger.info(f"Found {len(processing_docs)} documents in PROCESSING status with task_ids on startup")
            
            for doc in processing_docs:
                response_id, task_id, document_id, batch_id = doc
                if task_id:
                    # Add to active tasks for monitoring
                    self.active_tasks[task_id] = {
                        'doc_id': response_id,
                        'batch_id': batch_id,
                        'submitted_at': datetime.now(),  # Use current time as we don't know original
                        'document_id': document_id,
                        'poll_count': 0,
                        'recovered': True
                    }
                    logger.info(f"Recovered task {task_id} for llm_response {response_id}")
            
            kb_cursor.close()
            kb_conn.close()
            
            if self.active_tasks:
                logger.info(f"Recovered {len(self.active_tasks)} tasks for monitoring")
                logger.info(f"Active tasks after recovery: {list(self.active_tasks.keys())}")
            
        except Exception as e:
            logger.error(f"Error recovering processing documents: {e}")
        
    def stop(self):
        """Stop the queue processor"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=10)
        logger.info("BatchQueueProcessor stopped")
        
    def _process_loop(self):
        """Main processing loop"""
        logger.info("Queue processor loop started")
        
        while self.is_running:
            try:
                # Monitor batches ready for processing
                self._monitor_batches()
                
                # Check status of active tasks
                self._check_active_tasks()
                
                # Wait before next check
                time.sleep(self.check_interval)
                
            except Exception as e:
                logger.error(f"Error in processing loop: {e}", exc_info=True)
                time.sleep(self.check_interval)
                
        logger.info("Queue processor loop stopped")
        
    def _monitor_batches(self):
        """Monitor for batches ready for processing"""
        try:
            # Get batches ready for processing from BatchService
            ready_batches = batch_service.get_batches_ready_for_processing()
            
            if not ready_batches:
                return
                
            logger.info(f"Found {len(ready_batches)} batches ready for processing")
            
            # Process each batch if we have capacity
            for batch in ready_batches:
                if len(self.active_tasks) >= self.max_concurrent:
                    logger.debug(f"At max concurrent limit ({self.max_concurrent}), skipping batch {batch['batch_id']}")
                    break
                    
                self._process_batch_documents(batch['batch_id'])
                
        except Exception as e:
            logger.error(f"Error monitoring batches: {e}")
            
    def _process_batch_documents(self, batch_id: int):
        """Process documents from a specific batch"""
        try:
            # Keep processing documents while we have capacity
            while len(self.active_tasks) < self.max_concurrent:
                # Get next document from BatchService
                doc_info = batch_service.get_next_document_for_processing(batch_id)
                
                if not doc_info:
                    logger.debug(f"No more documents to process in batch {batch_id}")
                    break
                    
                # Submit document to RAG API
                task_id = self._submit_document_to_rag(doc_info)
                
                if task_id:
                    # Update BatchService with task_id
                    success = batch_service.update_document_task(
                        doc_info['response_id'], 
                        task_id, 
                        'PROCESSING'
                    )
                    
                    if success:
                        # Track active task
                        self.active_tasks[task_id] = {
                            'doc_id': doc_info['response_id'],
                            'batch_id': batch_id,
                            'submitted_at': datetime.now(),
                            'document_id': doc_info['document_id'],
                            'poll_count': 0
                        }
                        logger.info(f"✓ Submitted document {doc_info['response_id']} as task {task_id}")
                        logger.info(f"Active tasks count: {len(self.active_tasks)}")
                    else:
                        logger.error(f"Failed to update task_id for document {doc_info['response_id']}")
                else:
                    # Failed to submit, report to BatchService
                    error_data = {
                        'task_id': None,  # No task_id since submission failed
                        'doc_id': doc_info['response_id'],
                        'batch_id': batch_id,
                        'error': 'Failed to submit to RAG API'
                    }
                    batch_service.handle_task_failure(None, error_data)
                    self.stats['failed'] += 1
                    
        except Exception as e:
            logger.error(f"Error processing batch {batch_id} documents: {e}")
            
    def _submit_document_to_rag(self, doc_info: Dict[str, Any]) -> Optional[str]:
        """Submit document to RAG API and return task_id"""
        try:
            # Prepare form data for RAG API
            form_data = {
                'doc_id': doc_info['document_id'],
                'prompts': json.dumps([{"prompt": doc_info['prompt']['text']}]),
                'llm_provider': json.dumps(doc_info['llm_config']),
                'meta_data': json.dumps({})
            }
            
            logger.debug(f"Submitting to RAG API: doc_id={doc_info['document_id']}")
            
            # Make request to RAG API
            response = requests.post(
                f"{self.rag_api_url}/analyze_document_with_llm",
                data=form_data,
                timeout=30
            )
            
            if response.status_code == 200:
                result = response.json()
                task_id = result.get('task_id')
                
                if task_id:
                    logger.info(f"RAG API accepted document, task_id: {task_id}")
                    return task_id
                else:
                    logger.error(f"RAG API response missing task_id: {result}")
                    return None
            else:
                logger.error(f"RAG API returned {response.status_code}: {response.text}")
                return None
                
        except requests.exceptions.Timeout:
            logger.error("RAG API request timed out")
            return None
        except requests.exceptions.ConnectionError:
            logger.error("Could not connect to RAG API")
            return None
        except Exception as e:
            logger.error(f"Error submitting to RAG API: {e}")
            return None
            
    def _check_active_tasks(self):
        """Check status of all active tasks"""
        if not self.active_tasks:
            return
            
        logger.info(f"Checking {len(self.active_tasks)} active tasks")
        completed_tasks = []
        
        for task_id, task_info in self.active_tasks.items():
            try:
                # Increment poll count
                task_info['poll_count'] = task_info.get('poll_count', 0) + 1
                
                # Check for excessive polling (max 360 checks = 30 minutes at 5-second intervals)
                if task_info['poll_count'] > 360:
                    # Mark as failed due to excessive polling
                    error_data = {
                        'task_id': task_id,
                        'doc_id': task_info['doc_id'],
                        'batch_id': task_info['batch_id'],
                        'error': f'Task {task_id} exceeded maximum poll attempts (360)'
                    }
                    batch_service.handle_task_failure(task_id, error_data)
                    completed_tasks.append(task_id)
                    self.stats['failed'] += 1
                    logger.error(f"⚠️ Task {task_id} exceeded maximum poll attempts, marking as failed")
                    continue
                
                # Check for excessive 404 responses (if getting 404s for more than 12 polls = 1 minute, give up)
                if task_info.get('consecutive_404s', 0) > 12:
                    error_data = {
                        'task_id': task_id,
                        'doc_id': task_info['doc_id'],
                        'batch_id': task_info['batch_id'],
                        'error': f'Task {task_id} not found on RAG API (404) for over 1 minute'
                    }
                    batch_service.handle_task_failure(task_id, error_data)
                    completed_tasks.append(task_id)
                    self.stats['failed'] += 1
                    logger.error(f"⚠️ Task {task_id} has been returning 404 for over 1 minute, marking as failed")
                    continue
                
                status = self._check_task_status(task_id)
                
                # Track consecutive 404 responses
                if status.get('status') == 'http_404':
                    task_info['consecutive_404s'] = task_info.get('consecutive_404s', 0) + 1
                else:
                    task_info['consecutive_404s'] = 0
                
                if status['completed']:
                    # Task is done, report to BatchService
                    if status['success']:
                        # Extract response data and report completion
                        result_data = {
                            'task_id': task_id,
                            'doc_id': task_info['doc_id'],
                            'batch_id': task_info['batch_id'],
                            'response_text': status.get('response_text', ''),
                            'input_tokens': status.get('input_tokens', 0),
                            'output_tokens': status.get('output_tokens', 0),
                            'response_time_ms': status.get('response_time_ms', 0),
                            'overall_score': status.get('overall_score'),
                            'raw_response': status
                        }
                        
                        # Report to BatchService for centralized handling
                        batch_service.handle_task_completion(task_id, result_data)
                        
                        self.stats['processed'] += 1
                        self.stats['last_activity'] = datetime.now()
                        logger.info(f"✓ Task {task_id} completed successfully")
                    else:
                        # Task failed, report to BatchService
                        error_data = {
                            'task_id': task_id,
                            'doc_id': task_info['doc_id'],
                            'batch_id': task_info['batch_id'],
                            'error': status.get('error', 'Unknown error')
                        }
                        
                        # Report to BatchService for centralized handling
                        batch_service.handle_task_failure(task_id, error_data)
                        
                        self.stats['failed'] += 1
                        self.stats['last_activity'] = datetime.now()
                        logger.error(f"✗ Task {task_id} failed: {status.get('error')}")
                    
                    completed_tasks.append(task_id)
                    
                elif self._is_task_timeout(task_info):
                    # Task timeout, report to BatchService
                    error_data = {
                        'task_id': task_id,
                        'doc_id': task_info['doc_id'],
                        'batch_id': task_info['batch_id'],
                        'error': 'Task processing timeout'
                    }
                    
                    # Report to BatchService for centralized handling
                    batch_service.handle_task_failure(task_id, error_data)
                    
                    self.stats['failed'] += 1
                    completed_tasks.append(task_id)
                    logger.error(f"⏱ Task {task_id} timed out")
                    
            except Exception as e:
                logger.error(f"Error checking task {task_id}: {e}")
                
        # Remove completed tasks
        for task_id in completed_tasks:
            del self.active_tasks[task_id]
            
    def _check_task_status(self, task_id: str) -> Dict[str, Any]:
        """Check status of a specific task"""
        try:
            response = requests.get(
                f"{self.rag_api_url}/task_status/{task_id}",
                timeout=30  # Increased from 10 to 30 seconds
            )
            
            # Debug log for status code - only log non-200 responses
            if response.status_code != 200:
                logger.debug(f"Task {task_id} status check: HTTP {response.status_code}")
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                # Debug logging for status tracking
                if status not in ['processing', 'pending']:
                    logger.info(f"Task {task_id} status: {status}")
                
                if status in ['completed', 'success']:
                    # Extract response details
                    result = data.get('result', {})
                    analysis = result.get('data', {})
                    
                    return {
                        'completed': True,
                        'success': True,
                        'response_text': analysis.get('analysis', ''),
                        'input_tokens': analysis.get('input_tokens', 0),
                        'output_tokens': analysis.get('output_tokens', 0),
                        'response_time_ms': int(analysis.get('time_taken_seconds', 0) * 1000),
                        'overall_score': analysis.get('overall_score'),
                        'raw_data': data
                    }
                elif status == 'failed':
                    return {
                        'completed': True,
                        'success': False,
                        'error': data.get('error', 'Task failed')
                    }
                else:
                    # Still processing
                    return {
                        'completed': False,
                        'status': status
                    }
            elif response.status_code == 404:
                # Task not found - treat as failure (task may have been cleaned up or never existed)
                logger.warning(f"Task {task_id} not found (404) - treating as failed and removing from active tasks")
                return {
                    'completed': True,
                    'success': False,
                    'error': 'Task not found on RAG API (404)'
                }
            elif response.status_code in [400, 500, 502, 503]:
                # Client/server errors - treat as failure
                logger.error(f"Task {task_id} failed with HTTP {response.status_code}: {response.text}")
                return {
                    'completed': True,
                    'success': False,
                    'error': f'RAG API error ({response.status_code}): {response.text[:200]}'
                }
            else:
                # Other status codes - continue polling (might be temporary)
                logger.warning(f"Task status check returned {response.status_code}, continuing to poll (task_id: {task_id})")
                return {'completed': False, 'status': f'http_{response.status_code}'}
                
        except Exception as e:
            logger.error(f"Error checking task status: {e}")
            return {'completed': False, 'status': 'error'}
            
    def _is_task_timeout(self, task_info: Dict[str, Any], timeout_minutes: int = 30) -> bool:
        """Check if a task has timed out"""
        elapsed = datetime.now() - task_info['submitted_at']
        return elapsed.total_seconds() > (timeout_minutes * 60)

    def get_status(self) -> Dict[str, Any]:
        """Get processor status"""
        return {
            'is_running': self.is_running,
            'check_interval': self.check_interval,
            'max_concurrent': self.max_concurrent,
            'active_tasks': len(self.active_tasks),
            'stats': self.stats.copy(),
            'rag_api_url': self.rag_api_url
        }

    def process_stuck_items(self, stuck_threshold_minutes=30):
        """Handle stuck items by resetting them"""
        # This is now handled by BatchService checking completion status
        logger.info("Stuck item processing is handled by BatchService")
        return 0


# Global instance
batch_queue_processor = BatchQueueProcessor()


def start_queue_processor():
    """Start the global batch queue processor"""
    batch_queue_processor.start()
    

def stop_queue_processor():
    """Stop the global batch queue processor"""
    batch_queue_processor.stop()
    

def get_queue_processor_status():
    """Get status of the global batch queue processor"""
    return batch_queue_processor.get_status()