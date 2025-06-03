"""
KnowledgeDocuments Queue Processor

This service processes documents through BatchService coordination.
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


class KnowledgeQueueProcessor:
    """Process documents through BatchService coordination"""
    
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
        self.processing_thread = threading.Thread(target=self._process_loop)
        self.processing_thread.daemon = True
        self.processing_thread.start()
        
        logger.info("KnowledgeQueueProcessor started - using BatchService coordination")
        
    def stop(self):
        """Stop the queue processor"""
        self.is_running = False
        if self.processing_thread:
            self.processing_thread.join(timeout=10)
        logger.info("KnowledgeQueueProcessor stopped")
        
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
                            'document_id': doc_info['document_id']
                        }
                        logger.info(f"✓ Submitted document {doc_info['response_id']} as task {task_id}")
                    else:
                        logger.error(f"Failed to update task_id for document {doc_info['response_id']}")
                else:
                    # Failed to submit, update status
                    batch_service.update_document_status(
                        doc_info['response_id'],
                        'FAILED',
                        {'error': 'Failed to submit to RAG API'}
                    )
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
            
        completed_tasks = []
        
        for task_id, task_info in self.active_tasks.items():
            try:
                status = self._check_task_status(task_id)
                
                if status['completed']:
                    # Task is done, update BatchService
                    if status['success']:
                        # Extract response data
                        response_data = {
                            'response_text': status.get('response_text', ''),
                            'input_tokens': status.get('input_tokens', 0),
                            'output_tokens': status.get('output_tokens', 0),
                            'response_time_ms': status.get('response_time_ms', 0),
                            'overall_score': status.get('overall_score'),
                            'raw_response': status
                        }
                        
                        batch_service.update_document_status(
                            task_info['doc_id'],
                            'COMPLETED',
                            response_data
                        )
                        
                        self.stats['processed'] += 1
                        self.stats['last_activity'] = datetime.now()
                        logger.info(f"✓ Task {task_id} completed successfully")
                    else:
                        # Task failed
                        batch_service.update_document_status(
                            task_info['doc_id'],
                            'FAILED',
                            {'error': status.get('error', 'Unknown error')}
                        )
                        
                        self.stats['failed'] += 1
                        self.stats['last_activity'] = datetime.now()
                        logger.error(f"✗ Task {task_id} failed: {status.get('error')}")
                    
                    completed_tasks.append(task_id)
                    
                elif self._is_task_timeout(task_info):
                    # Task timeout
                    batch_service.update_document_status(
                        task_info['doc_id'],
                        'TIMEOUT',
                        {'error': 'Task processing timeout'}
                    )
                    
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
                timeout=10
            )
            
            if response.status_code == 200:
                data = response.json()
                status = data.get('status', 'unknown')
                
                if status == 'completed':
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
            else:
                logger.warning(f"Task status check returned {response.status_code}")
                return {'completed': False, 'status': 'unknown'}
                
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
knowledge_queue_processor = KnowledgeQueueProcessor()


def start_queue_processor():
    """Start the global queue processor"""
    knowledge_queue_processor.start()
    

def stop_queue_processor():
    """Stop the global queue processor"""
    knowledge_queue_processor.stop()
    

def get_queue_processor_status():
    """Get status of the global queue processor"""
    return knowledge_queue_processor.get_status()
            }
            
            logger.debug(f"Calling RAG API with doc_id: {document_id}")
            logger.debug(f"LLM Config being sent: {json.dumps(llm_config, indent=2)}")
            logger.debug(f"Form data: {form_data}")
            
            # Make request to RAG API with form encoding
            response = requests.post(
                f"{self.rag_api_url}/analyze_document_with_llm",
                data=form_data,  # Use data for form encoding, not json
                timeout=60
            )
            
            if response.status_code != 200:
                raise Exception(f"RAG API returned {response.status_code}: {response.text}")
                
            result = response.json()
            
            if not result.get('success', False):
                raise Exception(f"RAG API error: {result.get('error', 'Unknown error')}")
                
            return result.get('response', 'No response text')
            
        except requests.exceptions.Timeout:
            raise Exception("RAG API request timed out")
        except requests.exceptions.ConnectionError:
            raise Exception("Could not connect to RAG API")
        except Exception as e:
            raise Exception(f"RAG API call failed: {str(e)}")
            
    def _get_db_connection(self):
        """Get connection to KnowledgeDocuments database"""
        return psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        
    def process_stuck_items(self, stuck_threshold_minutes=30):
        """Reset stuck PROCESSING items back to QUEUED"""
        try:
            conn = self._get_db_connection()
            cursor = conn.cursor()
            
            # Reset stuck items
            cursor.execute("""
                UPDATE llm_responses 
                SET status = 'QUEUED',
                    started_processing_at = NULL,
                    task_id = NULL
                WHERE status = 'PROCESSING' 
                AND started_processing_at < NOW() - INTERVAL '%s minutes'
                RETURNING id, batch_id
            """, (stuck_threshold_minutes,))
            
            reset_items = cursor.fetchall()
            conn.commit()
            
            if reset_items:
                logger.info(f"Reset {len(reset_items)} stuck items to QUEUED")
                
            cursor.close()
            conn.close()
            
            return len(reset_items)
            
        except Exception as e:
            logger.error(f"Error processing stuck items: {e}")
            return 0


# Global instance
knowledge_queue_processor = KnowledgeQueueProcessor()


def start_queue_processor():
    """Start the global queue processor"""
    knowledge_queue_processor.start()
    

def stop_queue_processor():
    """Stop the global queue processor"""
    knowledge_queue_processor.stop()
    

def get_queue_processor_status():
    """Get status of the global queue processor"""
    return knowledge_queue_processor.get_status()