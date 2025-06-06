"""
Batch Service

Manages batch operations for document processing including:
- Creating new batches with timestamps
- Staging batches (preparing documents for LLM processing)
- Updating batch status and progress
- Retrieving batch information
- Managing batch lifecycle with timing data
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from sqlalchemy.sql import func
from sqlalchemy import and_, or_
from models import Batch, Document, Folder, Connection, Prompt, Model, LlmProvider
from database import Session
from services.document_encoding_service import DocumentEncodingService
from utils.llm_config_formatter import format_llm_config_for_rag_api
import os
import psycopg2
import base64

logger = logging.getLogger(__name__)

class BatchService:
    # Valid batch states
    BATCH_STATES = {
        'SAVED': 'Saved configuration',
        'STAGING': 'Preparing documents',
        'STAGED': 'Ready to process',
        'ANALYZING': 'Processing documents',
        'PAUSED': 'Processing paused',
        'COMPLETED': 'Processing complete',
        'FAILED': 'Processing failed',
        'FAILED_STAGING': 'Staging failed'
    }
    
    # Valid state transitions
    VALID_TRANSITIONS = {
        'SAVED': ['STAGING'],
        'STAGING': ['STAGED', 'FAILED_STAGING'],
        'STAGED': ['ANALYZING', 'STAGING'],  # Can restage
        'ANALYZING': ['COMPLETED', 'FAILED', 'PAUSED'],
        'PAUSED': ['ANALYZING', 'FAILED'],
        'COMPLETED': ['STAGING'],  # Can restage for rerun
        'FAILED': ['STAGING'],  # Can retry
        'FAILED_STAGING': ['STAGING']  # Can retry staging
    }
    
    # Actions that can be requested
    BATCH_ACTIONS = {
        'stage': 'Prepare batch for processing',
        'run': 'Start processing batch',
        'pause': 'Pause active processing',
        'resume': 'Resume paused processing',
        'reset': 'Reset batch to saved state',
        'cancel': 'Cancel active processing',
        'restage': 'Restage for reprocessing'
    }
    """Unified service for managing document processing batches including staging"""

    def __init__(self):
        logger.info("BatchService initialized - ready for unified batch and staging operations")
    
    def request_state_change(self, batch_id: int, action: str, context: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Central method for all batch state change requests.
        
        This is the ONLY method that should be used to change batch state.
        It validates the current state, checks if the transition is allowed,
        performs the transition if valid, and returns the result.
        
        Args:
            batch_id: The batch to modify
            action: The requested action (stage, run, pause, resume, reset, cancel, restage)
            context: Additional context for the action (e.g., user_id, reason)
            
        Returns:
            Dict with success, message, current_state, and other relevant data
        """
        if action not in self.BATCH_ACTIONS:
            return {
                'success': False,
                'error': f'Invalid action: {action}',
                'valid_actions': list(self.BATCH_ACTIONS.keys())
            }
        
        session = Session()
        try:
            # Lock the batch row to prevent concurrent modifications
            batch = session.query(Batch).filter(Batch.id == batch_id).with_for_update().first()
            if not batch:
                return {
                    'success': False,
                    'error': f'Batch {batch_id} not found'
                }
            
            current_state = batch.status
            logger.info(f"📋 State change requested for batch {batch_id}: {current_state} -> {action}")
            
            # Check if action is valid for current state
            can_proceed, reason = self._can_perform_action(batch, action, session)
            if not can_proceed:
                return {
                    'success': False,
                    'error': reason,
                    'current_state': current_state,
                    'batch_id': batch_id
                }
            
            # Perform the action
            result = self._perform_action(batch, action, context, session)
            
            # Log the state change
            if result.get('success'):
                new_state = batch.status
                logger.info(f"✅ Batch {batch_id} state changed: {current_state} -> {new_state} via {action}")
                result['previous_state'] = current_state
                result['new_state'] = new_state
            
            session.commit()
            return result
            
        except Exception as e:
            session.rollback()
            logger.error(f"Error in state change for batch {batch_id}: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Internal error: {str(e)}',
                'batch_id': batch_id
            }
        finally:
            session.close()
    
    def _can_perform_action(self, batch: Batch, action: str, session) -> Tuple[bool, str]:
        """Check if an action can be performed on a batch in its current state"""
        current_state = batch.status
        
        # Map actions to required states
        action_requirements = {
            'stage': ['SAVED', 'FAILED_STAGING'],
            'run': ['STAGED'],
            'pause': ['ANALYZING'],
            'resume': ['PAUSED'],
            'reset': ['SAVED', 'FAILED', 'FAILED_STAGING'],
            'cancel': ['ANALYZING', 'PAUSED', 'STAGING'],
            'restage': ['COMPLETED', 'FAILED', 'STAGED']
        }
        
        # Check if current state allows this action
        allowed_states = action_requirements.get(action, [])
        if current_state not in allowed_states:
            return False, f"Cannot {action} batch in {current_state} state. Allowed states: {', '.join(allowed_states)}"
        
        # Additional checks for specific actions
        if action == 'pause' and current_state == 'ANALYZING':
            # Check if there are actually active tasks to pause
            active_tasks = self._count_active_tasks(batch.id)
            if active_tasks == 0:
                return False, "No active tasks to pause"
        
        if action == 'reset' and current_state in ['ANALYZING', 'STAGING']:
            # Don't allow reset while actively processing
            return False, f"Cannot reset batch while {current_state}. Please wait for completion or use cancel action."
        
        return True, ""
    
    def _perform_action(self, batch: Batch, action: str, context: Optional[Dict[str, Any]], session) -> Dict[str, Any]:
        """Perform the requested action on the batch"""
        
        # Map actions to methods
        action_methods = {
            'stage': self._action_stage,
            'run': self._action_run,
            'pause': self._action_pause,
            'resume': self._action_resume,
            'reset': self._action_reset,
            'cancel': self._action_cancel,
            'restage': self._action_restage
        }
        
        method = action_methods.get(action)
        if not method:
            return {
                'success': False,
                'error': f'Action {action} not implemented'
            }
        
        return method(batch, context, session)
    
    def _count_active_tasks(self, batch_id: int) -> int:
        """Count active tasks for a batch in KnowledgeDocuments"""
        try:
            import psycopg2
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres", 
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            kb_cursor.execute("""
                SELECT COUNT(*) 
                FROM llm_responses 
                WHERE batch_id = %s 
                AND status IN ('QUEUED', 'P')
            """, (batch_id,))
            
            count = kb_cursor.fetchone()[0]
            kb_cursor.close()
            kb_conn.close()
            return count
        except Exception as e:
            logger.error(f"Error counting active tasks: {e}")
            return 0

    def _action_stage(self, batch: Batch, context: Optional[Dict[str, Any]], session) -> Dict[str, Any]:
        """Handle stage action - prepare documents"""
        batch.status = 'STAGING'
        session.flush()
        
        # Get connection and prompt IDs from batch config
        connection_ids = batch.config_snapshot.get('connection_ids', [])
        prompt_ids = batch.config_snapshot.get('prompt_ids', [])
        
        # Use existing staging logic
        encoding_service = DocumentEncodingService()
        staging_result = self._perform_staging(
            session, 
            batch.id, 
            batch.folder_ids or [], 
            connection_ids, 
            prompt_ids, 
            encoding_service
        )
        
        if staging_result['success']:
            batch.status = 'STAGED'
            return {
                'success': True,
                'message': f'Batch staged successfully',
                'total_documents': staging_result['total_documents'],
                'total_responses': staging_result['total_responses']
            }
        else:
            batch.status = 'FAILED_STAGING'
            return {
                'success': False,
                'error': staging_result.get('error', 'Staging failed')
            }
    
    def _action_run(self, batch: Batch, context: Optional[Dict[str, Any]], session) -> Dict[str, Any]:
        """Handle run action - start processing"""
        batch.status = 'ANALYZING'
        batch.started_at = func.now()
        session.flush()
        
        # The actual processing will be picked up by the queue processor
        return {
            'success': True,
            'message': 'Batch processing started',
            'batch_id': batch.id
        }
    
    def _action_pause(self, batch: Batch, context: Optional[Dict[str, Any]], session) -> Dict[str, Any]:
        """Handle pause action"""
        try:
            import psycopg2
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres", 
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Update QUEUED responses to PAUSED
            kb_cursor.execute("""
                UPDATE llm_responses 
                SET status = 'PAUSED' 
                WHERE batch_id = %s AND status IN ('QUEUED', 'P')
            """, (batch.id,))
            paused_count = kb_cursor.rowcount
            
            kb_conn.commit()
            kb_cursor.close()
            kb_conn.close()
            
            batch.status = 'PAUSED'
            
            return {
                'success': True,
                'message': f'Batch paused, {paused_count} tasks halted',
                'paused_tasks': paused_count
            }
        except Exception as e:
            logger.error(f"Error pausing batch: {e}")
            return {
                'success': False,
                'error': f'Failed to pause: {str(e)}'
            }
    
    def _action_resume(self, batch: Batch, context: Optional[Dict[str, Any]], session) -> Dict[str, Any]:
        """Handle resume action"""
        try:
            import psycopg2
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres", 
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Update PAUSED responses back to QUEUED
            kb_cursor.execute("""
                UPDATE llm_responses 
                SET status = 'QUEUED' 
                WHERE batch_id = %s AND status = 'PAUSED'
            """, (batch.id,))
            resumed_count = kb_cursor.rowcount
            
            kb_conn.commit()
            kb_cursor.close()
            kb_conn.close()
            
            batch.status = 'ANALYZING'
            
            return {
                'success': True,
                'message': f'Batch resumed, {resumed_count} tasks requeued',
                'resumed_tasks': resumed_count
            }
        except Exception as e:
            logger.error(f"Error resuming batch: {e}")
            return {
                'success': False,
                'error': f'Failed to resume: {str(e)}'
            }
    
    def _action_reset(self, batch: Batch, context: Optional[Dict[str, Any]], session) -> Dict[str, Any]:
        """Handle reset action - only allowed on non-active batches"""
        # This should only be called if batch is in allowed state (checked by _can_perform_action)
        
        # Clear any LLM responses if they exist
        try:
            import psycopg2
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres", 
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            kb_cursor.execute("DELETE FROM llm_responses WHERE batch_id = %s", (batch.id,))
            deleted_count = kb_cursor.rowcount
            
            kb_conn.commit()
            kb_cursor.close()
            kb_conn.close()
        except Exception as e:
            logger.warning(f"Error clearing LLM responses: {e}")
            deleted_count = 0
        
        # Reset batch state
        batch.status = 'SAVED'
        batch.started_at = None
        batch.completed_at = None
        batch.processed_documents = 0
        
        # Unassign documents
        documents = session.query(Document).filter(Document.batch_id == batch.id).all()
        for doc in documents:
            doc.batch_id = None
        
        return {
            'success': True,
            'message': 'Batch reset to saved state',
            'documents_unassigned': len(documents),
            'responses_deleted': deleted_count
        }
    
    def _action_cancel(self, batch: Batch, context: Optional[Dict[str, Any]], session) -> Dict[str, Any]:
        """Handle cancel action - stop active processing"""
        try:
            import psycopg2
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres", 
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Mark all QUEUED tasks as CANCELLED
            kb_cursor.execute("""
                UPDATE llm_responses 
                SET status = 'F', error_message = 'Cancelled by user' 
                WHERE batch_id = %s AND status IN ('QUEUED', 'P')
            """, (batch.id,))
            cancelled_count = kb_cursor.rowcount
            
            kb_conn.commit()
            kb_cursor.close()
            kb_conn.close()
            
            batch.status = 'FAILED'
            batch.completed_at = func.now()
            
            return {
                'success': True,
                'message': f'Batch cancelled, {cancelled_count} tasks stopped',
                'cancelled_tasks': cancelled_count
            }
        except Exception as e:
            logger.error(f"Error cancelling batch: {e}")
            return {
                'success': False,
                'error': f'Failed to cancel: {str(e)}'
            }
    
    def _action_restage(self, batch: Batch, context: Optional[Dict[str, Any]], session) -> Dict[str, Any]:
        """Handle restage action - prepare for reprocessing"""
        # Clear existing staging data
        try:
            import psycopg2
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres", 
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Delete existing llm_responses
            kb_cursor.execute("DELETE FROM llm_responses WHERE batch_id = %s", (batch.id,))
            kb_cursor.execute("DELETE FROM docs WHERE document_id LIKE %s", (f'batch_{batch.id}_%',))
            
            kb_conn.commit()
            kb_cursor.close()
            kb_conn.close()
        except Exception as e:
            logger.warning(f"Error clearing existing data: {e}")
        
        # Reset batch timing
        batch.started_at = None
        batch.completed_at = None
        batch.processed_documents = 0
        
        # Now stage again
        return self._action_stage(batch, context, session)
    
    def handle_task_completion(self, task_id: str, result_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle task completion from queue processor
        
        Args:
            task_id: The completed task ID
            result_data: Dict containing task results including response_text, tokens, etc.
            
        Returns:
            Dict with success status
        """
        try:
            import psycopg2
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres", 
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Update the llm_response with results
            kb_cursor.execute("""
                UPDATE llm_responses 
                SET status = 'COMPLETED',
                    response_text = %s,
                    response_json = %s,
                    input_tokens = %s,
                    output_tokens = %s,
                    response_time_ms = %s,
                    overall_score = %s,
                    completed_processing_at = NOW()
                WHERE task_id = %s
            """, (
                result_data.get('response_text', ''),
                json.dumps(result_data.get('raw_response', {})),
                result_data.get('input_tokens', 0),
                result_data.get('output_tokens', 0),
                result_data.get('response_time_ms', 0),
                result_data.get('overall_score'),
                task_id
            ))
            
            kb_conn.commit()
            kb_cursor.close()
            kb_conn.close()
            
            # Check if batch is complete
            self._check_batch_completion(result_data.get('batch_id'))
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error handling task completion: {e}")
            return {'success': False, 'error': str(e)}
    
    def handle_task_failure(self, task_id: Optional[str], error_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Handle task failure from queue processor
        
        Args:
            task_id: The failed task ID (can be None if submission failed)
            error_data: Dict containing error information
            
        Returns:
            Dict with success status
        """
        try:
            import psycopg2
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres", 
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            if task_id:
                # Update by task_id
                kb_cursor.execute("""
                    UPDATE llm_responses 
                    SET status = 'FAILED',
                        error_message = %s,
                        completed_processing_at = NOW()
                    WHERE task_id = %s
                """, (error_data.get('error', 'Unknown error'), task_id))
            else:
                # Update by doc_id if no task_id
                kb_cursor.execute("""
                    UPDATE llm_responses 
                    SET status = 'FAILED',
                        error_message = %s,
                        completed_processing_at = NOW()
                    WHERE id = %s
                """, (error_data.get('error', 'Unknown error'), error_data.get('doc_id')))
            
            kb_conn.commit()
            kb_cursor.close()
            kb_conn.close()
            
            # Check if batch is complete
            self._check_batch_completion(error_data.get('batch_id'))
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Error handling task failure: {e}")
            return {'success': False, 'error': str(e)}
    
    def _check_batch_completion(self, batch_id: int):
        """Check if all tasks for a batch are complete and update batch status"""
        if not batch_id:
            return
            
        try:
            import psycopg2
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres", 
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Check if any tasks are still pending
            kb_cursor.execute("""
                SELECT COUNT(*) 
                FROM llm_responses 
                WHERE batch_id = %s 
                AND status IN ('QUEUED', 'P', 'PROCESSING')
            """, (batch_id,))
            
            pending_count = kb_cursor.fetchone()[0]
            kb_cursor.close()
            kb_conn.close()
            
            if pending_count == 0:
                # All tasks complete, update batch status
                session = Session()
                try:
                    batch = session.query(Batch).filter(Batch.id == batch_id).first()
                    if batch and batch.status in ['ANALYZING', 'PROCESSING']:
                        batch.status = 'COMPLETED'
                        batch.completed_at = func.now()
                        session.commit()
                        logger.info(f"Batch {batch_id} marked as COMPLETED (was {batch.status})")
                finally:
                    session.close()
                    
        except Exception as e:
            logger.error(f"Error checking batch completion: {e}")
    
    def _handle_llm_response_deprecation(self, method_name: str) -> Dict[str, Any]:
        """Handle methods that depend on LlmResponse table"""
        logger.warning(f"{method_name} called but LLM processing has been moved to KnowledgeDocuments database")
        return {
            'success': False,
            'deprecated': True,
            'error': f'{method_name} functionality has been moved to KnowledgeDocuments database',
            'reason': 'llm_responses table moved to separate database'
        }

    def _create_config_snapshot(self, folder_ids: List[int]) -> Dict[str, Any]:
        """
        Create a complete configuration snapshot for a batch

        Args:
            folder_ids: List of folder IDs to include in the snapshot

        Returns:
            Dict containing complete configuration state
        """
        session = Session()
        try:
            # Get all active connections
            from sqlalchemy import text
            result = session.execute(text("""
                SELECT c.*, p.provider_type, m.display_name as model_name
                FROM connections c
                LEFT JOIN llm_providers p ON c.provider_id = p.id
                LEFT JOIN models m ON c.model_id = m.id
                WHERE c.is_active = true
            """))

            connections_data = []
            for row in result:
                connections_data.append({
                    'id': row.id,
                    'name': row.name,
                    'base_url': row.base_url,
                    'model_name': row.model_name or 'default',
                    'api_key': row.api_key,  # Note: Consider security implications
                    'provider_type': row.provider_type,
                    'port_no': row.port_no,
                    'is_active': row.is_active
                })

            # Get all active prompts
            prompts = session.query(Prompt).filter_by(active=1).all()
            prompts_data = []
            for prompt in prompts:
                prompts_data.append({
                    'id': prompt.id,
                    'prompt_text': prompt.prompt_text,
                    'description': prompt.description,
                    'active': prompt.active
                })

            # Get folders data
            folders_data = []
            documents_data = []

            if folder_ids:
                folders = session.query(Folder).filter(Folder.id.in_(folder_ids)).all()
                for folder in folders:
                    folder_data = {
                        'id': folder.id,
                        'folder_path': folder.folder_path,
                        'folder_name': folder.folder_name,
                        'active': folder.active,
                        'created_at': folder.created_at.isoformat() if folder.created_at else None
                    }
                    folders_data.append(folder_data)

                    # Get validated documents from preprocessing instead of scanning
                    # This ensures only properly validated files are included
                    validated_docs = session.query(Document).filter(
                        Document.folder_id == folder.id,
                        Document.valid == 'Y'  # Only include valid documents
                    ).all()
                    
                    for doc in validated_docs:
                        documents_data.append({
                            'filepath': doc.filepath,
                            'filename': doc.filename,
                            'folder_id': folder.id,
                            'relative_path': os.path.relpath(doc.filepath, folder.folder_path) if folder.folder_path else doc.filename,
                            'file_size': doc.meta_data.get('file_size', 0) if doc.meta_data else 0,
                            'document_id': doc.id,
                            'discovered_at': doc.created_at.isoformat() if doc.created_at else datetime.now().isoformat()
                        })

            # Create the complete snapshot
            config_snapshot = {
                'version': '1.0',
                'created_at': datetime.now().isoformat(),
                'connections': connections_data,
                'prompts': prompts_data,
                'folders': folders_data,
                'documents': documents_data,
                'summary': {
                    'total_connections': len(connections_data),
                    'total_prompts': len(prompts_data),
                    'total_folders': len(folders_data),
                    'total_documents': len(documents_data),
                    'expected_combinations': len(connections_data) * len(prompts_data) * len(documents_data)
                }
            }

            logger.info(f"Created config snapshot: {config_snapshot['summary']}")
            return config_snapshot

        finally:
            session.close()

    def create_multi_folder_batch(self, folder_ids: List[int], batch_name: Optional[str] = None, description: Optional[str] = None, meta_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        STAGE 1: Create and prepare a new batch for processing multiple folders
        - Creates batch record
        - Scans folders and creates document records
        - Encodes and stores all documents
        - Creates LLM response records
        - Sets status to PREPARED (ready to run)

        Args:
            folder_ids (List[int]): List of folder IDs to include in this batch
            batch_name (str, optional): User-friendly name for the batch
            description (str, optional): Description of the batch
            meta_data (Dict[str, Any], optional): JSON metadata to be sent to LLM for context

        Returns:
            Dict[str, Any]: The created batch data with preparation results
        """
        session = Session()

        try:
            # Get the next batch number
            max_batch_number = session.query(func.max(Batch.batch_number)).scalar()
            next_batch_number = (max_batch_number or 0) + 1

            # Generate default batch name if not provided
            if not batch_name:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                batch_name = f"Batch #{next_batch_number} - {timestamp}"

            # Create configuration snapshot
            config_snapshot = self._create_config_snapshot(folder_ids)

            # Create the batch with PREPARED status (Stage 1)
            batch = Batch(
                batch_number=next_batch_number,
                batch_name=batch_name,
                description=description,
                folder_ids=folder_ids,  # Keep for backward compatibility during transition
                folder_path=None,  # Legacy field, not used for multi-folder batches
                meta_data=meta_data,  # Store metadata as JSON
                config_snapshot=config_snapshot,  # Complete configuration state
                status='PREPARED',  # Stage 1: Prepared but not started
                started_at=None,  # Will be set when batch is actually run (Stage 2)
                total_documents=0,
                processed_documents=0
            )

            session.add(batch)
            session.flush()  # Get batch ID without committing

            logger.info(f"🔄 STAGE 1: Preparing batch #{next_batch_number} - {batch_name}")

            # STAGE 1: Get preprocessed document counts for folders
            folder_stats = {}
            total_valid_documents = 0

            folders = session.query(Folder).filter(Folder.id.in_(folder_ids)).all()
            for folder in folders:
                # Count valid documents from preprocessing
                valid_doc_count = session.query(Document).filter(
                    Document.folder_id == folder.id,
                    Document.valid == 'Y',
                    Document.batch_id.is_(None)
                ).count()
                
                folder_stats[folder.id] = {
                    'folder_name': folder.folder_name,
                    'folder_path': folder.folder_path,
                    'file_count': valid_doc_count
                }
                total_valid_documents += valid_doc_count
                logger.info(f"📁 Found {valid_doc_count} valid preprocessed documents in {folder.folder_name}")

            logger.info(f"📄 Total valid documents to process: {total_valid_documents}")

            # STAGE 1: Use existing preprocessed documents instead of creating new ones
            documents_created = 0
            responses_created = 0

            # Process each folder to get existing documents
            for folder_id in folder_ids:
                folder = session.query(Folder).filter(Folder.id == folder_id).first()
                if not folder:
                    logger.warning(f"⚠️ Folder {folder_id} not found, skipping")
                    continue

                # Get existing documents from the folder (from preprocessing)
                # Only include valid documents that have been validated during preprocessing
                existing_documents = session.query(Document).filter(
                    Document.folder_id == folder_id,
                    Document.batch_id.is_(None),  # Only get documents not already assigned to a batch
                    Document.valid == 'Y'  # Only include valid documents
                ).all()

                if not existing_documents:
                    logger.warning(f"⚠️ No unassigned preprocessed documents found for folder {folder_id}. Please preprocess the folder first.")
                    continue

                logger.info(f"📄 Using {len(existing_documents)} preprocessed documents from {folder.folder_name}")

                # Update existing documents to link to this batch
                for document in existing_documents:
                    # Update the document to link to this batch
                    document.batch_id = batch.id
                    documents_created += 1

                    # LLM response creation moved to KnowledgeDocuments database
                    # Skip creating LLM responses since they're handled in separate database
                    logger.info(f"📄 Document {document.filename} prepared (LLM responses handled in KnowledgeDocuments database)")

                    # Count expected responses for reporting (but don't create them)
                    prompts = config_snapshot['prompts']
                    connections = config_snapshot['connections']
                    expected_responses = len(prompts) * len(connections)
                    responses_created += expected_responses

            # Update batch totals
            batch.total_documents = documents_created

            session.commit()

            logger.info(f"✅ STAGE 1 COMPLETE: Batch #{next_batch_number} prepared")
            logger.info(f"   📄 Documents created: {documents_created}")
            logger.info(f"   🔗 LLM responses created: {responses_created}")
            logger.info(f"   📊 Folder breakdown: {folder_stats}")

            # Extract data before closing session
            batch_data = {
                'id': batch.id,
                'batch_number': batch.batch_number,
                'batch_name': batch.batch_name,
                'description': batch.description,
                'folder_ids': batch.folder_ids,
                'meta_data': batch.meta_data,
                'config_snapshot': batch.config_snapshot,
                'status': batch.status,
                'preparation_results': {
                    'documents_created': documents_created,
                    'responses_created': responses_created,
                    'folder_stats': folder_stats,
                    'documents_used': f"{documents_created} existing preprocessed documents"
                }
            }

            return batch_data

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error in STAGE 1 batch preparation: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def run_batch(self, batch_id: int) -> Dict[str, Any]:
        """
        Start execution of a batch - handles both READY and PREPARED status batches
        For READY batches: Creates LLM responses and starts processing
        For PREPARED batches: Starts processing existing LLM responses
        """
        session = Session()
        try:
            # Get the batch
            batch = session.query(Batch).filter(Batch.id == batch_id).first()
            if not batch:
                return {
                    'success': False,
                    'error': f'Batch {batch_id} not found'
                }

            logger.info(f"🚀 Starting execution of batch #{batch.batch_number} (Status: {batch.status})")

            # Handle different batch statuses
            if batch.status == 'READY':
                # Batch is ready but not staged - create documents and llm_responses
                return self._run_ready_batch(session, batch)
            elif batch.status == 'STAGED':
                # Batch has been staged - llm_responses already exist, just process them
                return self._run_staged_batch(session, batch)
            else:
                return {
                    'success': False,
                    'error': f'Batch {batch_id} cannot be run from status {batch.status}. Expected READY, STAGED, or PREPARED.'
                }

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error running batch {batch_id}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def _run_staged_batch(self, session, batch) -> Dict[str, Any]:
        """Handle running a batch with STAGED status - process existing llm_responses"""
        try:
            logger.info(f"🔄 Processing staged batch #{batch.batch_number}")
            
            # Update batch status to ANALYZING
            batch.status = 'ANALYZING'
            batch.started_at = func.now()
            session.commit()
            
            # Connect to KnowledgeDocuments database to get llm_responses
            import psycopg2
            import json
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Get all QUEUED or PAUSED llm_responses for this batch
            kb_cursor.execute("""
                SELECT lr.id, lr.document_id, lr.prompt_id, lr.connection_id, 
                       d.document_id as doc_ref_id, lr.status
                FROM llm_responses lr
                JOIN docs d ON lr.document_id = d.id
                WHERE lr.batch_id = %s AND lr.status IN ('QUEUED', 'PAUSED')
            """, (batch.id,))
            
            queued_responses = kb_cursor.fetchall()
            logger.info(f"Found {len(queued_responses)} queued responses to process")
            
            if not queued_responses:
                kb_cursor.close()
                kb_conn.close()
                
                batch.status = 'COMPLETED'
                batch.completed_at = func.now()
                session.commit()
                
                return {
                    'success': True,
                    'batch_id': batch.id,
                    'batch_number': batch.batch_number,
                    'batch_name': batch.batch_name,
                    'message': 'No queued responses to process',
                    'total_responses': 0
                }
            
            # Get connection details from batch config
            connections_map = {}
            if batch.config_snapshot and 'connections' in batch.config_snapshot:
                for conn in batch.config_snapshot['connections']:
                    connections_map[conn['id']] = conn
            
            # Get prompt details from batch config
            prompts_map = {}
            if batch.config_snapshot and 'prompts' in batch.config_snapshot:
                for prompt in batch.config_snapshot['prompts']:
                    prompts_map[prompt['id']] = prompt
            
            # Process each queued response
            processed_count = 0
            failed_count = 0
            
            for response in queued_responses:
                lr_id, doc_id, prompt_id, conn_id, doc_ref_id, lr_status = response
                
                try:
                    # Get connection config
                    connection = connections_map.get(conn_id, {})
                    
                    # Use unified formatter for LLM config
                    llm_config = format_llm_config_for_rag_api(connection)
                    
                    # Prepare prompts
                    prompt = prompts_map.get(prompt_id, {})
                    prompts_data = [{'prompt': prompt.get('prompt_text', '')}]
                    
                    # Prepare metadata
                    meta_data = {
                        'batch_id': batch.id,
                        'batch_name': batch.batch_name,
                        'llm_response_id': lr_id,
                        **(batch.meta_data or {})
                    }
                    
                    logger.info(f"📤 Sending llm_response {lr_id} (doc: {doc_id}) to RAG API")
                    logger.info(f"   LLM Config: provider={llm_config['provider_type']}, url={llm_config['url']}, model={llm_config['model_name']}")
                    
                    # Send to RAG API
                    form_data = {
                        'doc_id': str(doc_id),
                        'prompts': json.dumps(prompts_data),
                        'llm_provider': json.dumps(llm_config),
                        'meta_data': json.dumps(meta_data)
                    }
                    
                    import requests
                    response_raw = requests.post(
                        "http://localhost:7001/analyze_document_with_llm",
                        data=form_data,
                        headers={'Content-Type': 'application/x-www-form-urlencoded'},
                        timeout=120
                    )
                    
                    if response_raw.status_code < 400:
                        # Update llm_response status to PROCESSING
                        kb_cursor.execute("""
                            UPDATE llm_responses 
                            SET status = 'PROCESSING', 
                                task_id = %s,
                                started_processing_at = NOW()
                            WHERE id = %s
                        """, (
                            response_raw.json().get('task_id', ''),
                            lr_id
                        ))
                        kb_conn.commit()
                        processed_count += 1
                        logger.info(f"✅ Successfully submitted llm_response {lr_id} for processing")
                    else:
                        failed_count += 1
                        logger.error(f"❌ Failed to submit llm_response {lr_id}: HTTP {response_raw.status_code}")
                        
                except Exception as e:
                    failed_count += 1
                    logger.error(f"❌ Error processing llm_response {lr_id}: {e}")
            
            kb_cursor.close()
            kb_conn.close()
            
            # Update batch status
            if processed_count > 0:
                batch.status = 'ANALYZING'
                message = f"Submitted {processed_count} responses for processing"
            else:
                batch.status = 'FAILED'
                message = f"Failed to submit any responses for processing"
            
            session.commit()
            
            logger.info(f"✅ Batch processing initiated: {processed_count} successful, {failed_count} failed")
            
            return {
                'success': True,
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'batch_name': batch.batch_name,
                'message': message,
                'processed_count': processed_count,
                'failed_count': failed_count,
                'total_responses': len(queued_responses)
            }
            
        except Exception as e:
            logger.error(f"❌ Error in _run_staged_batch: {e}", exc_info=True)
            batch.status = 'FAILED'
            session.commit()
            return {
                'success': False,
                'error': str(e)
            }

    def _run_ready_batch(self, session, batch) -> Dict[str, Any]:
        """Handle running a batch with READY status - create LLM responses and start processing"""
        try:
            # Check if batch has config snapshot with required data
            if not batch.config_snapshot or not batch.config_snapshot.get('connections') or not batch.config_snapshot.get('prompts'):
                return {
                    'success': False,
                    'error': f'Batch {batch.id} does not have valid configuration snapshot. Missing connections or prompts. Cannot create LLM responses.'
                }

            # Update batch status to ANALYZING
            batch.status = 'ANALYZING'
            batch.started_at = func.now()

            # Get documents in this batch
            documents = session.query(Document).filter(Document.batch_id == batch.id).all()
            if not documents:
                return {
                    'success': False,
                    'error': f'No documents found in batch {batch.id}'
                }

            # Get connections and prompts from config snapshot
            # Use the snapshot data to ensure consistency - connections and prompts should NOT change after batch creation
            connections = batch.config_snapshot.get('connections', [])
            prompts = batch.config_snapshot.get('prompts', [])

            logger.info(f"✅ Batch #{batch.batch_number} marked as ANALYZING")
            logger.info(f"   📄 Documents ready: {len(documents)}")
            logger.info(f"   🔗 Connections: {len(connections)}")
            logger.info(f"   📝 Prompts: {len(prompts)}")
            logger.info(f"🚀 Processing {len(documents)} documents with {len(connections)} connections and {len(prompts)} prompts")

            # Import RAG service client
            from services.client import RAGServiceClient, RequestMethod
            rag_client = RAGServiceClient()

            processed_count = 0
            failed_count = 0

            # Process each document with each connection/prompt combination
            for document in documents:
                for connection in connections:
                    for prompt in prompts:
                        try:
                            # Use unified formatter for LLM config
                            llm_config = format_llm_config_for_rag_api(connection)

                            # Prepare prompts data
                            prompts_data = [{'prompt': prompt.get('prompt_text', '')}]

                            # Create document in KnowledgeDocuments database and send to RAG API
                            import os
                            import mimetypes
                            import base64
                            import psycopg2
                            import json

                            if not os.path.exists(document.filepath):
                                logger.error(f"❌ File not found: {document.filepath}")
                                failed_count += 1
                                continue

                            # Prepare metadata
                            meta_data = {
                                'batch_id': batch.id,
                                'batch_name': batch.batch_name,
                                'document_id': document.id,
                                'connection_id': connection.get('id'),
                                'prompt_id': prompt.get('id'),
                                **(batch.meta_data or {})
                            }

                            logger.info(f"🔄 Creating document in KnowledgeDocuments database and sending to RAG API: {document.filename}")

                            try:
                                # Read and encode file content
                                with open(document.filepath, 'rb') as file:
                                    file_content = file.read()

                                # Check file size before encoding
                                file_size = len(file_content)
                                logger.info(f"📄 File size: {file_size} bytes ({file_size / 1024 / 1024:.2f} MB)")
                                
                                # Determine MIME type and doc type
                                content_type = mimetypes.guess_type(document.filepath)[0] or 'application/octet-stream'
                                _, ext = os.path.splitext(document.filepath.lower())
                                doc_type = ext[1:] if ext.startswith('.') else ext

                                # Encode content as base64 and decode to string
                                try:
                                    encoded_content = base64.b64encode(file_content).decode('utf-8')
                                    logger.info(f"📄 Encoded content length: {len(encoded_content)} characters")
                                    
                                    # Ensure proper base64 padding
                                    # Base64 strings must have length divisible by 4
                                    remainder = len(encoded_content) % 4
                                    if remainder != 0:
                                        # This should not happen with standard base64 encoding, but let's handle it
                                        padding_needed = 4 - remainder
                                        logger.warning(f"⚠️ Base64 string needs {padding_needed} padding characters (length: {len(encoded_content)})")
                                        encoded_content += '=' * padding_needed
                                        logger.info(f"🔧 Added padding, new length: {len(encoded_content)}")
                                    
                                    # Validate the encoded content by trying to decode it
                                    try:
                                        test_decode = base64.b64decode(encoded_content)
                                        if len(test_decode) != file_size:
                                            logger.error(f"❌ Decoded size mismatch: expected {file_size}, got {len(test_decode)}")
                                            failed_count += 1
                                            continue
                                        logger.info(f"✅ Base64 validation passed")
                                    except Exception as decode_error:
                                        logger.error(f"❌ Base64 validation failed: {decode_error}")
                                        failed_count += 1
                                        continue
                                        
                                except Exception as encode_error:
                                    logger.error(f"❌ Failed to encode file content: {encode_error}")
                                    failed_count += 1
                                    continue

                                # Connect to KnowledgeDocuments database
                                conn = None
                                cursor = None
                                try:
                                    conn = psycopg2.connect(
                                        host="studio.local",
                                        database="KnowledgeDocuments",
                                        user="postgres",
                                        password="prodogs03",
                                        port=5432
                                    )
                                    cursor = conn.cursor()
                                except Exception as db_error:
                                    logger.error(f"❌ Failed to connect to KnowledgeDocuments database: {db_error}")
                                    failed_count += 1
                                    continue

                                # Create unique document_id for this batch document
                                unique_doc_id = f"batch_{batch.id}_doc_{document.id}"

                                # Check if document already exists by document_id
                                cursor.execute("SELECT id FROM docs WHERE document_id = %s", (unique_doc_id,))
                                existing_doc = cursor.fetchone()

                                if existing_doc:
                                    doc_id = existing_doc[0]
                                    logger.info(f"📄 Document already exists in KnowledgeDocuments database with ID: {doc_id}")
                                else:
                                    # Insert document into docs table using correct column names
                                    try:
                                        # Log the size of data being inserted
                                        logger.info(f"📊 Inserting document: content_length={len(encoded_content)}, file_size={file_size}")
                                        
                                        # Strip any whitespace that might have been added
                                        encoded_content_clean = encoded_content.strip()
                                        if len(encoded_content_clean) != len(encoded_content):
                                            logger.warning(f"⚠️ Stripped whitespace from encoded content: {len(encoded_content)} -> {len(encoded_content_clean)}")
                                        
                                        # Double-check the length is valid for base64
                                        if len(encoded_content_clean) % 4 != 0:
                                            logger.error(f"❌ Invalid base64 length after cleaning: {len(encoded_content_clean)} (mod 4 = {len(encoded_content_clean) % 4})")
                                            # Try to fix by padding
                                            padding_needed = 4 - (len(encoded_content_clean) % 4)
                                            encoded_content_clean += '=' * padding_needed
                                            logger.info(f"🔧 Added {padding_needed} padding characters, new length: {len(encoded_content_clean)}")
                                        
                                        cursor.execute("""
                                            INSERT INTO docs (content, content_type, doc_type, file_size, encoding, created_at, document_id)
                                            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
                                            RETURNING id
                                        """, (
                                            encoded_content_clean,  # Use cleaned content
                                            content_type,
                                            doc_type,
                                            file_size,  # Use the variable we calculated earlier
                                            'base64',
                                            unique_doc_id
                                        ))
                                        doc_id = cursor.fetchone()[0]
                                        conn.commit()
                                        logger.info(f"✅ Document created in KnowledgeDocuments database with ID: {doc_id}")
                                    except Exception as insert_error:
                                        logger.error(f"❌ Failed to insert document into KnowledgeDocuments database: {insert_error}")
                                        logger.error(f"📏 Document details: file={document.filepath}, encoded_size={len(encoded_content)}, file_size={file_size}")
                                        if conn:
                                            conn.rollback()
                                        failed_count += 1
                                        if cursor:
                                            cursor.close()
                                        if conn:
                                            conn.close()
                                        continue

                                if cursor:
                                    cursor.close()
                                if conn:
                                    conn.close()

                                # Now send to RAG API with the doc_id
                                # We already have llm_config from line 568
                                logger.info(f"🔧 Sending to RAG API with config: {llm_config}")

                                # Prepare form data for RAG API (expects form-encoded with JSON strings)
                                form_data = {
                                    'doc_id': str(doc_id),  # Convert to string as required by API
                                    'prompts': json.dumps(prompts_data),  # JSON string as required
                                    'llm_provider': json.dumps(llm_config),  # JSON string as required
                                    'meta_data': json.dumps(meta_data) if meta_data else None  # Optional field
                                }

                                # Remove None values
                                form_data = {k: v for k, v in form_data.items() if v is not None}

                                # Send to RAG API as form data
                                import requests
                                response_raw = requests.post(
                                    "http://localhost:7001/analyze_document_with_llm",
                                    data=form_data,  # Use data for form encoding
                                    headers={'Content-Type': 'application/x-www-form-urlencoded'},
                                    timeout=120
                                )

                                # Convert to ServiceResponse format
                                if response_raw.status_code < 400:
                                    try:
                                        response_data = response_raw.json() if response_raw.content else {}
                                    except ValueError:
                                        response_data = {"raw_response": response_raw.text}

                                    response = type('ServiceResponse', (), {
                                        'success': True,
                                        'status_code': response_raw.status_code,
                                        'data': response_data,
                                        'error_message': None
                                    })()
                                else:
                                    response = type('ServiceResponse', (), {
                                        'success': False,
                                        'status_code': response_raw.status_code,
                                        'data': None,
                                        'error_message': f"HTTP {response_raw.status_code}: {response_raw.text[:200]}"
                                    })()

                            except Exception as e:
                                logger.error(f"❌ Error creating document or sending to RAG API: {e}")
                                response = type('ServiceResponse', (), {
                                    'success': False,
                                    'status_code': None,
                                    'data': None,
                                    'error_message': str(e)
                                })()

                            if response.success:
                                processed_count += 1
                                logger.info(f"✅ Successfully queued document {document.filename} for processing")
                                if hasattr(response, 'data') and response.data:
                                    task_id = response.data.get('task_id')
                                    if task_id:
                                        logger.info(f"📋 Task ID: {task_id}")
                                        
                                        # Create llm_responses record in KnowledgeDocuments database
                                        try:
                                            import psycopg2
                                            kb_conn = psycopg2.connect(
                                                host="studio.local",
                                                database="KnowledgeDocuments",
                                                user="postgres",
                                                password="prodogs03",
                                                port=5432
                                            )
                                            kb_cursor = kb_conn.cursor()
                                            
                                            kb_cursor.execute("""
                                                INSERT INTO llm_responses 
                                                (document_id, prompt_id, connection_id, connection_details, task_id, status, started_processing_at, batch_id)
                                                VALUES (%s, %s, %s, %s, %s, %s, NOW(), %s)
                                            """, (
                                                doc_id,  # Using KnowledgeDocuments doc_id
                                                prompt.get('id'),
                                                connection.get('id'),
                                                json.dumps(llm_config),
                                                task_id,
                                                'QUEUED',  # Initial status
                                                batch.id  # Add batch_id
                                            ))
                                            kb_conn.commit()
                                            kb_cursor.close()
                                            kb_conn.close()
                                            
                                            logger.info(f"📝 Created llm_responses record for task {task_id}")
                                            
                                            # Start background polling for this task
                                            self._start_task_polling(
                                                task_id=task_id,
                                                doc_id=doc_id,
                                                connection_id=connection.get('id'),
                                                prompt_id=prompt.get('id'),
                                                connection_details=llm_config
                                            )
                                            
                                        except Exception as e:
                                            logger.error(f"❌ Failed to create llm_responses record: {e}")
                            else:
                                failed_count += 1
                                error_msg = getattr(response, 'error_message', 'Unknown error')
                                if hasattr(response, 'data') and response.data:
                                    error_msg = response.data.get('detail', error_msg)
                                logger.error(f"❌ Failed to queue document {document.filename}: {error_msg}")

                        except Exception as e:
                            failed_count += 1
                            logger.error(f"❌ Error processing document {document.filename}: {e}")

            # Update batch progress
            batch.processed_documents = processed_count
            session.commit()

            logger.info(f"✅ Batch processing initiated: {processed_count} successful, {failed_count} failed")

            return {
                'success': True,
                'batch_id': batch.id,
                'batch_number': batch.batch_number,
                'batch_name': batch.batch_name,
                'status': batch.status,
                'message': f'Batch #{batch.batch_number} started successfully',
                'execution_results': {
                    'total_documents': len(documents),
                    'total_combinations': len(documents) * len(connections) * len(prompts),
                    'successfully_queued': processed_count,
                    'failed_to_queue': failed_count,
                    'connections_used': len(connections),
                    'prompts_used': len(prompts)
                }
            }

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error running ready batch {batch.id}: {e}", exc_info=True)
            raise



    def rerun_batch(self, batch_id: int) -> Dict[str, Any]:
        """
        Rerun analysis for a batch following the complete workflow:
        1. Delete all llm_responses associated with batch
        2. Recreate llm_response shells  
        3. Refresh documents replacing records where files have newer timestamp
        4. Refresh docs replacing records where files have newer timestamp
        5. Run Analysis on Batch
        
        Args:
            batch_id (int): ID of the batch to rerun
            
        Returns:
            Dict[str, Any]: Execution results and status
        """
        logger.info(f"🔄 RERUN: Starting complete rerun analysis for batch {batch_id}")
        
        try:
            session = Session()
            
            # Get the batch and validate it exists
            batch = session.query(Batch).filter(Batch.id == batch_id).first()
            if not batch:
                session.close()
                return {'success': False, 'error': f'Batch {batch_id} not found'}
            
            logger.info(f"🔄 Found batch #{batch.batch_number} - {batch.batch_name}")
            
            # Step 1: Delete all llm_responses associated with batch from KnowledgeDocuments
            import psycopg2
            import json
            
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres", 
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Step 1: Delete ALL existing LLM responses for this batch
            # First, count what we have
            kb_cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE batch_id = %s", (batch_id,))
            before_count = kb_cursor.fetchone()[0]
            logger.info(f"🔍 Found {before_count} existing LLM responses for batch {batch_id}")
            
            # Delete all responses
            kb_cursor.execute("DELETE FROM llm_responses WHERE batch_id = %s", (batch_id,))
            deleted_responses = kb_cursor.rowcount
            
            # Verify deletion
            kb_cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE batch_id = %s", (batch_id,))
            after_count = kb_cursor.fetchone()[0]
            
            logger.info(f"🗑️ Deleted {deleted_responses} LLM responses")
            logger.info(f"🔍 Verification: {before_count} → {after_count} responses remaining")
            
            if after_count > 0:
                logger.warning(f"⚠️ Warning: {after_count} LLM responses still remain for batch {batch_id}")
                # Try a more aggressive delete
                kb_cursor.execute("DELETE FROM llm_responses WHERE batch_id = %s", (batch_id,))
                additional_deleted = kb_cursor.rowcount
                if additional_deleted > 0:
                    logger.info(f"🗑️ Deleted {additional_deleted} additional responses on second attempt")
                    deleted_responses += additional_deleted
            
            # Step 3: Refresh documents - check for newer files and update records
            documents = session.query(Document).filter(Document.batch_id == batch_id).all()
            logger.info(f"📄 Checking {len(documents)} documents for file updates")
            
            refreshed_docs = 0
            for doc in documents:
                if os.path.exists(doc.filepath):
                    file_mtime = os.path.getmtime(doc.filepath)
                    file_modified = datetime.fromtimestamp(file_mtime)
                    
                    # If file is newer than document record, we'll refresh it in KB docs
                    # Document model only has created_at, so compare against that
                    # Handle timezone-aware comparison
                    doc_created = doc.created_at
                    if doc_created and hasattr(doc_created, 'replace'):
                        doc_created = doc_created.replace(tzinfo=None)
                    
                    if not doc_created or file_modified > doc_created:
                        logger.info(f"📄 Document file is newer: {doc.filename}")
                        refreshed_docs += 1
                else:
                    logger.warning(f"⚠️ File not found for document: {doc.filepath}")
            
            logger.info(f"📄 Found {refreshed_docs} documents with newer files")
            
            # Step 4: Refresh docs in KnowledgeDocuments - re-encode files with newer timestamps
            refreshed_kb_docs = 0
            for doc in documents:
                if not os.path.exists(doc.filepath):
                    continue
                    
                file_mtime = os.path.getmtime(doc.filepath)
                file_modified = datetime.fromtimestamp(file_mtime)
                
                # Check if we need to refresh the KB doc
                doc_id = f"batch_{batch_id}_doc_{doc.id}"
                kb_cursor.execute("SELECT created_at FROM docs WHERE document_id = %s", (doc_id,))
                kb_result = kb_cursor.fetchone()
                
                kb_created = kb_result[0] if kb_result else None
                if kb_created and hasattr(kb_created, 'replace'):
                    kb_created = kb_created.replace(tzinfo=None)
                
                if not kb_created or file_modified > kb_created:
                    logger.info(f"📄 Refreshing KB doc: {doc.filename}")
                    
                    # Re-read and encode the file
                    with open(doc.filepath, 'rb') as f:
                        file_content = f.read()
                    
                    import base64
                    encoded_content = base64.b64encode(file_content).decode('utf-8')
                    
                    # Clean encoded content - ensure it's valid base64
                    encoded_content = encoded_content.strip()
                    if len(encoded_content) % 4 != 0:
                        encoded_content += '=' * (4 - len(encoded_content) % 4)
                    
                    # Update the docs table
                    kb_cursor.execute("""
                        INSERT INTO docs (document_id, content, content_type, doc_type, file_size, encoding, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (document_id) DO UPDATE
                        SET content = EXCLUDED.content,
                            file_size = EXCLUDED.file_size,
                            created_at = NOW()
                    """, (
                        doc_id,
                        encoded_content,
                        'text/plain',
                        os.path.splitext(doc.filename)[1][1:] if '.' in doc.filename else 'txt',
                        len(file_content),
                        'base64'
                    ))
                    refreshed_kb_docs += 1
            
            logger.info(f"📄 Refreshed {refreshed_kb_docs} KB document records")
            
            # Step 2: Recreate llm_response shells from batch configuration
            if not batch.config_snapshot:
                session.close()
                kb_conn.close()
                return {
                    'success': False,
                    'error': 'Batch has no configuration snapshot. Cannot recreate LLM responses.'
                }
            
            config = batch.config_snapshot
            connection_ids = [c['id'] for c in config.get('connections', [])]
            prompt_ids = [p['id'] for p in config.get('prompts', [])]
            
            logger.info(f"🔄 Recreating LLM responses for {len(connection_ids)} connections × {len(prompt_ids)} prompts")
            
            # Get updated document IDs from KnowledgeDocuments
            kb_cursor.execute("""
                SELECT id, document_id FROM docs 
                WHERE document_id LIKE %s
            """, (f'batch_{batch_id}_doc_%',))
            kb_docs = kb_cursor.fetchall()
            kb_doc_map = {doc_id: kb_id for kb_id, doc_id in kb_docs}
            
            created_responses = 0
            for doc in documents:
                doc_id_pattern = f"batch_{batch_id}_doc_{doc.id}"
                kb_doc_id = kb_doc_map.get(doc_id_pattern)
                
                if not kb_doc_id:
                    logger.warning(f"⚠️ No KB document found for {doc_id_pattern}")
                    continue
                
                for conn_id in connection_ids:
                    # Get connection details
                    connection = session.query(Connection).filter_by(id=conn_id).first()
                    if not connection:
                        continue
                        
                    # Get connection config safely
                    connection_config = connection.connection_config or {}
                    
                    # Get model and provider details for LLM config
                    model_name = 'default'
                    provider_type = 'ollama'
                    
                    if connection.model_id:
                        model = session.query(Model).filter_by(id=connection.model_id).first()
                        if model:
                            model_name = model.display_name
                    
                    if connection.provider_id:
                        provider = session.query(LlmProvider).filter_by(id=connection.provider_id).first()
                        if provider:
                            provider_type = provider.provider_type
                    
                    conn_details = {
                        'id': connection.id,
                        'name': connection.name,
                        'provider_id': connection.provider_id,
                        'model_id': connection.model_id,
                        'model_name': model_name,
                        'provider_type': provider_type,
                        'api_key': connection.api_key,
                        'base_url': connection.base_url,
                        'port_no': connection.port_no,
                        'temperature': connection_config.get('temperature'),
                        'max_tokens': connection_config.get('max_tokens')
                    }
                    
                    for prompt_id in prompt_ids:
                        kb_cursor.execute("""
                            INSERT INTO llm_responses 
                            (document_id, prompt_id, connection_id, connection_details, 
                             status, created_at, batch_id)
                            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
                        """, (
                            kb_doc_id,
                            prompt_id,
                            conn_id,
                            json.dumps(conn_details),
                            'QUEUED',
                            batch_id
                        ))
                        created_responses += 1
            
            kb_conn.commit()
            logger.info(f"✅ Created {created_responses} new LLM response shells")
            
            # Step 5: Update batch status to trigger analysis
            batch.status = 'STAGED'  # Ready for external processing
            session.commit()
            
            # Build response while session is still active
            response_data = {
                'success': True,
                'batch_id': batch_id,
                'batch_number': batch.batch_number,
                'batch_name': batch.batch_name,
                'deleted_responses': deleted_responses,
                'refreshed_documents': refreshed_docs,
                'refreshed_kb_docs': refreshed_kb_docs,
                'created_responses': created_responses,
                'status': 'STAGED',
                'message': f'Batch {batch_id} prepared for rerun analysis with {created_responses} responses'
            }
            
            # Close connections
            session.close()
            kb_cursor.close()
            kb_conn.close()
            
            logger.info(f"✅ RERUN: Completed rerun analysis setup for batch {batch_id}")
            
            return response_data
            
        except Exception as e:
            logger.error(f"❌ Error in rerun_batch for batch {batch_id}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'batch_id': batch_id
            }

    def create_batch(self, folder_path: str, batch_name: Optional[str] = None, description: Optional[str] = None, meta_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Create a new batch for document processing

        Args:
            folder_path (str): Path of the folder being processed
            batch_name (str, optional): User-friendly name for the batch
            description (str, optional): Description of the batch
            meta_data (Dict[str, Any], optional): JSON metadata to be sent to LLM for context

        Returns:
            Dict[str, Any]: The created batch data (id, batch_number, batch_name)
        """
        session = Session()
        try:
            # Get the next batch number
            max_batch_number = session.query(func.max(Batch.batch_number)).scalar()
            next_batch_number = (max_batch_number or 0) + 1

            # Generate default batch name if not provided
            if not batch_name:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                batch_name = f"Batch #{next_batch_number} - {timestamp}"

            # Create the batch
            batch = Batch(
                batch_number=next_batch_number,
                batch_name=batch_name,
                description=description,
                folder_path=folder_path,
                meta_data=meta_data,  # Store metadata as JSON
                status='P',  # Processing
                started_at=func.now(),  # Mark when processing started
                total_documents=0,
                processed_documents=0
            )

            session.add(batch)
            session.commit()

            # Extract data before closing session
            batch_data = {
                'id': batch.id,
                'batch_number': batch.batch_number,
                'batch_name': batch.batch_name,
                'description': batch.description,
                'folder_path': batch.folder_path,
                'meta_data': batch.meta_data,
                'status': batch.status
            }

            logger.info(f"Created new batch: #{next_batch_number} - {batch_name} for folder: {folder_path}")
            return batch_data

        except Exception as e:
            session.rollback()
            logger.error(f"Error creating batch: {e}", exc_info=True)
            raise
        finally:
            session.close()

    def get_real_time_batch_progress(self, batch_id: int) -> Optional[Dict[str, Any]]:
        """
        Get comprehensive real-time progress for a specific batch

        Args:
            batch_id (int): ID of the batch to get progress for

        Returns:
            Dict[str, Any]: Comprehensive batch progress information
        """
        session = Session()
        try:
            # Get batch info
            batch = session.query(Batch).filter(Batch.id == batch_id).first()
            if not batch:
                return None

            # Get all documents in this batch
            documents = session.query(Document).filter(Document.batch_id == batch_id).all()
            total_documents = len(documents)

            # Get ALL LLM response statistics (not just those with response times)
            all_response_stats = session.query(
                LlmResponse.status,
                func.count(LlmResponse.id).label('count')
            ).join(Document).filter(
                Document.batch_id == batch_id
            ).group_by(LlmResponse.status).all()

            # Get timing statistics for completed responses only
            timing_stats = session.query(
                LlmResponse.status,
                func.avg(LlmResponse.response_time_ms).label('avg_time'),
                func.min(LlmResponse.response_time_ms).label('min_time'),
                func.max(LlmResponse.response_time_ms).label('max_time')
            ).join(Document).filter(
                Document.batch_id == batch_id,
                LlmResponse.response_time_ms.isnot(None)
            ).group_by(LlmResponse.status).all()

            # Process response statistics
            status_counts = {}
            processing_times = {}

            # Get all response counts (including those without timing)
            for stat in all_response_stats:
                status_counts[stat.status] = stat.count

            # Get timing data for responses that have been processed
            for stat in timing_stats:
                if stat.avg_time:
                    processing_times[stat.status] = {
                        'avg_ms': round(stat.avg_time, 2),
                        'min_ms': stat.min_time,
                        'max_ms': stat.max_time
                    }

            # Calculate overall progress based on ALL responses
            total_responses = sum(status_counts.values())
            completed_responses = status_counts.get('S', 0)  # Success
            failed_responses = status_counts.get('F', 0)     # Failed
            processing_responses = status_counts.get('P', 0) # Processing
            ready_responses = status_counts.get('N', 0)      # Not started (was 'R' but should be 'N')

            # Calculate document-level progress (how many documents are fully processed)
            # A document is considered "completed" when ALL its responses are either Success or Failed
            completed_documents = 0
            failed_documents = 0
            processing_documents = 0
            waiting_documents = 0

            for document in documents:
                doc_responses = session.query(LlmResponse).filter(
                    LlmResponse.document_id == document.id
                ).all()

                if not doc_responses:
                    waiting_documents += 1
                    continue

                # Check if all responses for this document are completed (S or F)
                all_completed = all(r.status in ['S', 'F'] for r in doc_responses)
                any_processing = any(r.status == 'P' for r in doc_responses)

                if all_completed:
                    # Check if document has any successful responses
                    has_success = any(r.status == 'S' for r in doc_responses)
                    if has_success:
                        completed_documents += 1
                    else:
                        failed_documents += 1
                elif any_processing:
                    processing_documents += 1
                else:
                    waiting_documents += 1

            # Calculate folder-level progress if batch has folder_ids
            folder_progress = []
            if batch.folder_ids:
                for folder_id in batch.folder_ids:
                    folder = session.query(Folder).filter(Folder.id == folder_id).first()
                    if folder:
                        folder_docs = session.query(Document).filter(
                            Document.folder_id == folder_id,
                            Document.batch_id == batch_id
                        ).all()

                        folder_responses = session.query(LlmResponse).join(Document).filter(
                            Document.folder_id == folder_id,
                            Document.batch_id == batch_id
                        ).all()

                        folder_completed = len([r for r in folder_responses if r.status == 'S'])
                        folder_failed = len([r for r in folder_responses if r.status == 'F'])
                        folder_processing = len([r for r in folder_responses if r.status == 'P'])
                        folder_total = len(folder_responses)

                        folder_progress.append({
                            'folder_id': folder_id,
                            'folder_name': folder.folder_name,
                            'folder_path': folder.folder_path,
                            'total_documents': len(folder_docs),
                            'total_responses': folder_total,
                            'completed': folder_completed,
                            'failed': folder_failed,
                            'processing': folder_processing,
                            'progress_percent': round((folder_completed + folder_failed) / folder_total * 100, 1) if folder_total > 0 else 0
                        })

            # Calculate timing statistics
            elapsed_time = None
            estimated_completion = None
            if batch.started_at:
                elapsed_seconds = (datetime.utcnow() - batch.started_at).total_seconds()
                elapsed_time = {
                    'seconds': int(elapsed_seconds),
                    'minutes': round(elapsed_seconds / 60, 1),
                    'hours': round(elapsed_seconds / 3600, 2)
                }

                # Estimate completion time based on current progress
                if completed_responses > 0 and total_responses > completed_responses:
                    avg_time_per_doc = elapsed_seconds / completed_responses
                    remaining_docs = total_responses - completed_responses
                    estimated_seconds = remaining_docs * avg_time_per_doc
                    estimated_completion = {
                        'seconds': int(estimated_seconds),
                        'minutes': round(estimated_seconds / 60, 1),
                        'hours': round(estimated_seconds / 3600, 2)
                    }

            return {
                'batch_id': batch_id,
                'batch_number': batch.batch_number,
                'batch_name': batch.batch_name,
                'status': batch.status,
                'created_at': batch.created_at.isoformat() if batch.created_at else None,
                'started_at': batch.started_at.isoformat() if batch.started_at else None,
                'completed_at': batch.completed_at.isoformat() if batch.completed_at else None,
                'elapsed_time': elapsed_time,
                'estimated_completion': estimated_completion,
                'documents': {
                    'total': total_documents,
                    'completed': completed_documents,
                    'failed': failed_documents,
                    'processing': processing_documents,
                    'waiting': waiting_documents,
                    'with_responses': total_responses
                },
                'responses': {
                    'total': total_responses,
                    'completed': completed_responses,
                    'failed': failed_responses,
                    'processing': processing_responses,
                    'waiting': ready_responses,
                    'progress_percent': round((completed_documents + failed_documents) / total_documents * 100, 1) if total_documents > 0 else 0,
                    'success_rate': round(completed_documents / (completed_documents + failed_documents) * 100, 1) if (completed_documents + failed_documents) > 0 else 0
                },
                'processing_times': processing_times,
                'folder_progress': folder_progress,
                'performance': {
                    'avg_processing_time_ms': processing_times.get('S', {}).get('avg_ms', 0),
                    'throughput_docs_per_minute': round(completed_documents / (elapsed_time['minutes'] if elapsed_time and elapsed_time['minutes'] > 0 else 1), 2) if elapsed_time else 0
                }
            }

        except Exception as e:
            logger.error(f"Error getting real-time batch progress for batch {batch_id}: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def get_all_active_batches_progress(self) -> List[Dict[str, Any]]:
        """
        Get real-time progress for all active (processing) batches

        Returns:
            List[Dict[str, Any]]: List of batch progress information
        """
        session = Session()
        try:
            # Get all processing and paused batches
            active_batches = session.query(Batch).filter(Batch.status.in_(['P', 'PA'])).all()

            progress_list = []
            for batch in active_batches:
                progress = self.get_real_time_batch_progress(batch.id)
                if progress:
                    progress_list.append(progress)

            return progress_list

        except Exception as e:
            logger.error(f"Error getting all active batches progress: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_batch_summary_stats(self, batch_ids: Optional[List[int]] = None) -> Dict[str, Any]:
        """
        Get overall batch processing statistics - LLM response data moved to KnowledgeDocuments database

        Args:
            batch_ids (List[int], optional): Filter statistics to specific batch IDs

        Returns:
            Dict[str, Any]: Summary statistics across all batches or filtered batches (without LLM response data)
        """
        session = Session()
        try:
            # Build base queries with optional batch filtering
            batch_filter = Batch.id.in_(batch_ids) if batch_ids else True
            document_filter = Document.batch_id.in_(batch_ids) if batch_ids else True

            # Get batch counts by status
            batch_counts = session.query(
                Batch.status,
                func.count(Batch.id).label('count')
            ).filter(batch_filter).group_by(Batch.status).all()

            status_counts = {status: count for status, count in batch_counts}

            # Get overall document counts
            total_batches = session.query(Batch).filter(batch_filter).count()
            total_documents = session.query(Document).filter(document_filter).count()

            # Get recent activity (last 24 hours)
            from datetime import timedelta
            day_ago = datetime.utcnow() - timedelta(days=1)
            recent_batches = session.query(Batch).filter(
                and_(Batch.created_at >= day_ago, batch_filter)
            ).count()

            recent_documents = session.query(Document).filter(
                and_(Document.created_at >= day_ago, document_filter)
            ).count()

            # Return stats without LLM response data (moved to KnowledgeDocuments database)
            return {
                'total_batches': total_batches,
                'batch_status_counts': status_counts,
                'total_documents': total_documents,
                'total_responses': 0,  # LLM responses moved to KnowledgeDocuments database
                'response_status_counts': {},  # LLM responses moved to KnowledgeDocuments database
                'avg_processing_time_ms': 0,  # LLM response timing moved to KnowledgeDocuments database
                'recent_activity': {
                    'batches_24h': recent_batches,
                    'documents_24h': recent_documents
                },
                'success_rate': 0,  # LLM response success rate moved to KnowledgeDocuments database
                'active_batches': status_counts.get('P', 0),
                'filtered_batch_ids': batch_ids,
                'deprecated_notice': 'LLM response statistics moved to KnowledgeDocuments database'
            }

        except Exception as e:
            logger.error(f"Error getting batch summary stats: {e}", exc_info=True)
            return {}
        finally:
            session.close()

    def update_batch_name(self, batch_id: int, batch_name: str, description: Optional[str] = None) -> bool:
        """
        Update the name and description of an existing batch

        Args:
            batch_id (int): ID of the batch to update
            batch_name (str): New name for the batch
            description (str, optional): New description for the batch

        Returns:
            bool: True if successful, False otherwise
        """
        session = Session()
        try:
            batch = session.query(Batch).filter_by(id=batch_id).first()
            if not batch:
                logger.error(f"Batch {batch_id} not found")
                return False

            batch.batch_name = batch_name
            if description is not None:
                batch.description = description

            session.commit()
            logger.info(f"Updated batch #{batch.batch_number}: {batch_name}")
            return True

        except Exception as e:
            session.rollback()
            logger.error(f"Error updating batch {batch_id}: {e}", exc_info=True)
            return False
        finally:
            session.close()

    def pause_batch(self, batch_id: int) -> Dict[str, Any]:
        """
        Pause a batch - stops new documents from being submitted but allows current processing to continue

        Args:
            batch_id (int): ID of the batch to pause

        Returns:
            dict: Result of the pause operation
        """
        session = Session()
        try:
            batch = session.query(Batch).filter_by(id=batch_id).first()
            if not batch:
                return {'success': False, 'error': f'Batch {batch_id} not found'}

            if batch.status not in ['ANALYZING', 'PROCESSING', 'STAGED']:
                return {'success': False, 'error': f'Batch {batch_id} is not currently processing (status: {batch.status}). Can only pause ANALYZING, PROCESSING, or STAGED batches.'}

            # Update llm_responses status in KnowledgeDocuments database
            try:
                import psycopg2
                kb_conn = psycopg2.connect(
                    host="studio.local",
                    database="KnowledgeDocuments",
                    user="postgres",
                    password="prodogs03",
                    port=5432
                )
                kb_cursor = kb_conn.cursor()
                
                # Update PROCESSING responses to PAUSED
                kb_cursor.execute("""
                    UPDATE llm_responses 
                    SET status = 'PAUSED' 
                    WHERE batch_id = %s AND status = 'PROCESSING'
                """, (batch_id,))
                paused_count = kb_cursor.rowcount
                
                kb_conn.commit()
                kb_cursor.close()
                kb_conn.close()
                
                logger.info(f"Updated {paused_count} llm_responses to PAUSED status")
            except Exception as e:
                logger.error(f"Error updating llm_response statuses: {e}")

            batch.status = 'PAUSED'  # Paused
            session.commit()

            logger.info(f"Paused batch {batch_id} (#{batch.batch_number} - '{batch.batch_name}')")
            return {
                'success': True,
                'message': f'Batch {batch.batch_number} paused successfully',
                'batch_id': batch_id,
                'status': 'PAUSED'
            }

        except Exception as e:
            logger.error(f"Error pausing batch {batch_id}: {e}", exc_info=True)
            session.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def resume_batch(self, batch_id: int) -> Dict[str, Any]:
        """
        Resume a paused batch or restart a failed batch - sends documents to RAG API for processing

        Args:
            batch_id (int): ID of the batch to resume

        Returns:
            dict: Result of the resume operation
        """
        session = Session()
        try:
            batch = session.query(Batch).filter_by(id=batch_id).first()
            if not batch:
                return {'success': False, 'error': f'Batch {batch_id} not found'}

            # Allow resuming PAUSED, ANALYZING, or STAGED batches
            if batch.status not in ['PAUSED', 'ANALYZING', 'STAGED']:
                return {'success': False, 'error': f'Batch {batch_id} cannot be resumed (status: {batch.status}). Can only resume PAUSED, ANALYZING, or STAGED batches.'}

            logger.info(f"🔄 Resuming batch {batch_id} (#{batch.batch_number} - '{batch.batch_name}') from status {batch.status}")

            # Determine how to process based on whether batch has been staged
            if batch.status == 'STAGED':
                # Batch has been staged - use _run_staged_batch to process existing llm_responses
                result = self._run_staged_batch(session, batch)
            else:
                # For PAUSED/ANALYZING batches, check if llm_responses exist
                import psycopg2
                kb_conn = psycopg2.connect(
                    host="studio.local",
                    database="KnowledgeDocuments",
                    user="postgres",
                    password="prodogs03",
                    port=5432
                )
                kb_cursor = kb_conn.cursor()
                
                # Check if llm_responses exist for this batch
                kb_cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE batch_id = %s", (batch.id,))
                llm_response_count = kb_cursor.fetchone()[0]
                kb_cursor.close()
                kb_conn.close()
                
                if llm_response_count > 0:
                    # llm_responses exist - process them without creating new ones
                    batch.status = 'STAGED'  # Set to STAGED since responses exist
                    session.commit()
                    result = self._run_staged_batch(session, batch)
                else:
                    # No llm_responses - need to create them
                    batch.status = 'ANALYZING'
                    batch.started_at = func.now()
                    session.commit()
                    result = self._process_batch_with_rag_api(session, batch)

            if result['success']:
                logger.info(f"✅ Batch {batch_id} resumed and processing initiated successfully")
                return {
                    'success': True,
                    'message': f'Batch {batch.batch_number} resumed and processing initiated',
                    'batch_id': batch_id,
                    'status': 'ANALYZING',
                    'processing_results': result.get('processing_results', {})
                }
            else:
                logger.error(f"❌ Failed to process batch {batch_id} after resume: {result.get('error')}")
                batch.status = 'FAILED'
                session.commit()
                return {
                    'success': False,
                    'error': f'Failed to process batch after resume: {result.get("error")}',
                    'batch_id': batch_id
                }

        except Exception as e:
            logger.error(f"Error resuming batch {batch_id}: {e}", exc_info=True)
            session.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def reset_batch_to_prestage(self, batch_id: int) -> Dict[str, Any]:
        """
        Reset a stuck batch back to prestage (SAVED) state

        This allows the user to restart a batch that got stuck in any processing state.
        The batch will be reset to SAVED status and can be staged and run again.

        Args:
            batch_id (int): ID of the batch to reset

        Returns:
            Dict[str, Any]: Result of the reset operation
        """
        session = Session()
        try:
            batch = session.query(Batch).filter_by(id=batch_id).first()
            if not batch:
                return {'success': False, 'error': f'Batch {batch_id} not found'}

            # Don't allow resetting completed batches (use restage-and-rerun instead)
            if batch.status == 'COMPLETED':
                return {
                    'success': False,
                    'error': f'Batch {batch_id} is completed. Use "Restage & Rerun" instead of reset for completed batches.'
                }
            
            # Don't allow resetting actively processing batches
            if batch.status in ['PROCESSING', 'ANALYZING']:
                # Check if there are active tasks in KnowledgeDocuments
                import psycopg2
                try:
                    kb_conn = psycopg2.connect(
                        host="studio.local",
                        database="KnowledgeDocuments",
                        user="postgres", 
                        password="prodogs03",
                        port=5432
                    )
                    kb_cursor = kb_conn.cursor()
                    
                    # Check for any QUEUED or in-progress tasks
                    kb_cursor.execute("""
                        SELECT COUNT(*) 
                        FROM llm_responses 
                        WHERE batch_id = %s 
                        AND status IN ('QUEUED', 'P')
                    """, (batch_id,))
                    
                    active_count = kb_cursor.fetchone()[0]
                    kb_cursor.close()
                    kb_conn.close()
                    
                    if active_count > 0:
                        return {
                            'success': False,
                            'error': f'Batch {batch_id} has {active_count} active tasks still processing. Please wait for completion or pause the batch first.'
                        }
                except Exception as e:
                    logger.warning(f"Could not check active tasks: {e}")
                
                # Even if we can't check, warn about resetting active batch
                return {
                    'success': False,
                    'error': f'Batch {batch_id} is currently {batch.status}. Please wait for processing to complete or pause the batch first.',
                    'current_status': batch.status
                }

            logger.info(f"🔄 RESET: Resetting batch {batch_id} (#{batch.batch_number} - '{batch.batch_name}') from status {batch.status} to SAVED")

            # Store original status for logging
            original_status = batch.status
            
            # Step 1: Delete ALL LLM responses associated with this batch from KnowledgeDocuments
            import psycopg2
            deleted_responses = 0
            
            try:
                kb_conn = psycopg2.connect(
                    host="studio.local",
                    database="KnowledgeDocuments",
                    user="postgres", 
                    password="prodogs03",
                    port=5432
                )
                kb_cursor = kb_conn.cursor()
                
                # Delete ALL LLM responses for this batch
                kb_cursor.execute("DELETE FROM llm_responses WHERE batch_id = %s", (batch_id,))
                deleted_responses = kb_cursor.rowcount
                kb_conn.commit()
                kb_cursor.close()
                kb_conn.close()
                
                logger.info(f"🗑️ RESET: Deleted {deleted_responses} LLM responses from KnowledgeDocuments")
                
            except Exception as e:
                logger.error(f"Error deleting LLM responses during reset: {e}")
                # Continue with reset even if LLM response deletion fails

            # Step 2: Reset batch to prestage state
            batch.status = 'SAVED'
            batch.started_at = None  # Clear start time
            batch.completed_at = None  # Clear completion time
            batch.processed_documents = 0  # Reset progress counter

            # Keep total_documents count if it exists (from previous staging)
            # Keep config_snapshot (the batch configuration)
            # Keep folder_ids and meta_data (the batch definition)

            session.commit()

            # Step 3: Unassign documents from this batch so they can be reassigned during next staging
            documents = session.query(Document).filter(Document.batch_id == batch_id).all()
            documents_unassigned = 0

            for document in documents:
                document.batch_id = None  # Unassign from batch
                documents_unassigned += 1

            session.commit()

            logger.info(f"✅ RESET: Batch {batch_id} reset successfully")
            logger.info(f"   Status: {original_status} → SAVED")
            logger.info(f"   LLM responses deleted: {deleted_responses}")
            logger.info(f"   Documents unassigned: {documents_unassigned}")
            logger.info(f"   Batch can now be staged and run again")

            return {
                'success': True,
                'message': f'Batch {batch.batch_number} reset to prestage state successfully',
                'batch_id': batch_id,
                'batch_number': batch.batch_number,
                'batch_name': batch.batch_name,
                'original_status': original_status,
                'new_status': 'SAVED',
                'deleted_responses': deleted_responses,
                'documents_unassigned': documents_unassigned,
                'next_steps': 'Batch is now ready for staging. Use "Stage Batch" to prepare it for analysis.'
            }

        except Exception as e:
            logger.error(f"Error resetting batch {batch_id} to prestage: {e}", exc_info=True)
            session.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def _process_batch_with_rag_api(self, session: Session, batch: Batch) -> Dict[str, Any]:
        """
        Process batch documents using the external RAG API service

        Args:
            session: Database session
            batch: Batch object to process

        Returns:
            Dict with success status and processing results
        """
        try:
            # Get batch configuration
            config_snapshot = batch.config_snapshot or {}
            connections = config_snapshot.get('connections', [])
            prompts = config_snapshot.get('prompts', [])

            if not connections or not prompts:
                return {
                    'success': False,
                    'error': 'Batch configuration incomplete - missing connections or prompts'
                }

            # Get documents in this batch
            documents = session.query(Document).filter(Document.batch_id == batch.id).all()

            if not documents:
                return {
                    'success': False,
                    'error': 'No documents found in batch'
                }

            logger.info(f"🚀 Processing {len(documents)} documents with {len(connections)} connections and {len(prompts)} prompts")

            # Import RAG service client
            from services.client import RAGServiceClient, RequestMethod
            rag_client = RAGServiceClient()

            processed_count = 0
            failed_count = 0

            # Process each document with each connection/prompt combination
            for document in documents:
                for connection in connections:
                    for prompt in prompts:
                        try:
                            # Use unified formatter for LLM config
                            llm_config = format_llm_config_for_rag_api(connection)

                            # Prepare prompts data
                            prompts_data = [{'prompt': prompt.get('prompt_text', '')}]

                            # Create a doc_id that the RAG API can use to find the document
                            # Since docs table is in separate database, we'll use the document filepath as identifier
                            doc_identifier = document.filepath

                            # Prepare metadata
                            meta_data = {
                                'batch_id': batch.id,
                                'batch_name': batch.batch_name,
                                'document_id': document.id,
                                'connection_id': connection.get('id'),
                                'prompt_id': prompt.get('id'),
                                **(batch.meta_data or {})
                            }

                            logger.info(f"🔄 Sending document {document.filename} to RAG API with {connection.get('name', 'Unknown Connection')}")

                            # Call RAG API service - send as form data by including empty files dict
                            import json
                            form_data = {
                                'doc_id': str(doc_identifier),  # Convert to string
                                'prompts': json.dumps(prompts_data),  # Convert to JSON string
                                'llm_provider': json.dumps(llm_config),  # Convert to JSON string
                                'meta_data': json.dumps(meta_data)  # Convert to JSON string
                            }

                            response = rag_client.client.call_service(
                                service_name="rag_api",
                                endpoint="/analyze_document_with_llm",
                                method=RequestMethod.POST,
                                data=form_data,
                                files={},  # Empty files dict to force form data encoding
                                timeout=120  # Longer timeout for document processing
                            )

                            if response.success:
                                processed_count += 1
                                logger.info(f"✅ Successfully queued document {document.filename} for processing")
                                if hasattr(response, 'data') and response.data:
                                    task_id = response.data.get('task_id')
                                    if task_id:
                                        logger.info(f"📋 Task ID: {task_id}")
                            else:
                                failed_count += 1
                                error_msg = getattr(response, 'error', 'Unknown error')
                                if hasattr(response, 'data') and response.data:
                                    error_msg = response.data.get('detail', error_msg)
                                logger.error(f"❌ Failed to queue document {document.filename}: {error_msg}")

                        except Exception as e:
                            failed_count += 1
                            logger.error(f"❌ Error processing document {document.filename}: {e}")

            # Update batch progress
            batch.processed_documents = processed_count
            session.commit()

            logger.info(f"✅ Batch processing initiated: {processed_count} successful, {failed_count} failed")

            return {
                'success': True,
                'processing_results': {
                    'total_documents': len(documents),
                    'total_combinations': len(documents) * len(connections) * len(prompts),
                    'successfully_queued': processed_count,
                    'failed_to_queue': failed_count,
                    'connections_used': len(connections),
                    'prompts_used': len(prompts)
                }
            }

        except Exception as e:
            logger.error(f"❌ Error in _process_batch_with_rag_api: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def update_batch_progress(self, batch_id: int) -> Dict[str, Any]:
        """
        Update batch progress based on document processing status

        Args:
            batch_id (int): ID of the batch to update

        Returns:
            dict: Updated batch statistics
        """
        session = Session()
        try:
            batch = session.query(Batch).filter_by(id=batch_id).first()
            if not batch:
                logger.error(f"Batch {batch_id} not found")
                return {}

            # Count documents in this batch
            total_documents = session.query(Document).filter_by(batch_id=batch_id).count()

            # LLM response counting moved to KnowledgeDocuments database
            completed_responses = 0  # LLM response data moved to KnowledgeDocuments database
            total_responses = 0  # LLM response data moved to KnowledgeDocuments database

            # Update batch statistics
            batch.total_documents = total_documents
            batch.processed_documents = completed_responses

            # Update batch status (but don't override paused status)
            if batch.status != 'PA':  # Don't change status if paused
                if total_responses > 0:
                    completion_percentage = (completed_responses / total_responses) * 100
                    if completion_percentage >= 100:
                        batch.status = 'COMPLETED'  # Use new COMPLETED status
                        batch.completed_at = func.now()
                    elif completion_percentage > 0:
                        # Keep current status if analyzing, otherwise use legacy processing
                        if batch.status not in ['ANALYZING']:
                            batch.status = 'P'  # Processing (legacy)
                    else:
                        # Keep current status if analyzing, otherwise use legacy processing
                        if batch.status not in ['ANALYZING']:
                            batch.status = 'P'  # Processing (just started, legacy)
                else:
                    # No responses - this indicates a problem with batch setup
                    # Don't automatically mark as completed, keep current status
                    # This prevents batches from showing as completed when they have no LLM responses
                    logger.warning(f"Batch {batch_id} has no LLM responses - keeping current status: {batch.status}")
                    # Only mark as completed if batch was explicitly set to a final status
                    if batch.status in ['FAILED_STAGING', 'STAGED']:
                        # These are valid final states that might have no responses
                        pass
                    else:
                        # For other statuses, this indicates an issue
                        logger.error(f"Batch {batch_id} has no LLM responses but status is {batch.status}")
                        # Consider setting to an error state or keeping current status

            session.commit()

            return {
                'batch_id': batch_id,
                'batch_number': batch.batch_number,
                'batch_name': batch.batch_name,
                'total_documents': total_documents,
                'processed_responses': completed_responses,
                'total_responses': total_responses,
                'completion_percentage': (completed_responses / total_responses * 100) if total_responses > 0 else 0,
                'status': batch.status
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Error updating batch progress {batch_id}: {e}", exc_info=True)
            return {}
        finally:
            session.close()

    def get_batch_info(self, batch_id: int) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a batch

        Args:
            batch_id (int): ID of the batch

        Returns:
            dict: Batch information or None if not found
        """
        session = Session()
        try:
            batch = session.query(Batch).filter_by(id=batch_id).first()
            if not batch:
                return None

            # Get document count
            document_count = session.query(Document).filter_by(batch_id=batch_id).count()

            # Get LLM response statistics from KnowledgeDocuments database
            total_responses = 0
            status_counts = {}
            completion_percentage = 0
            
            try:
                import psycopg2
                kb_conn = psycopg2.connect(
                    host="studio.local",
                    database="KnowledgeDocuments",
                    user="postgres",
                    password="prodogs03",
                    port=5432
                )
                kb_cursor = kb_conn.cursor()
                
                # Get total count of LLM responses for this batch
                kb_cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE batch_id = %s", (batch_id,))
                total_responses = kb_cursor.fetchone()[0]
                
                # Get status counts
                kb_cursor.execute("""
                    SELECT status, COUNT(*) 
                    FROM llm_responses 
                    WHERE batch_id = %s 
                    GROUP BY status
                """, (batch_id,))
                
                for status, count in kb_cursor.fetchall():
                    status_counts[status] = count
                
                # Calculate completion percentage
                completed_count = status_counts.get('S', 0) + status_counts.get('F', 0)
                if total_responses > 0:
                    completion_percentage = round((completed_count / total_responses) * 100)
                
                kb_cursor.close()
                kb_conn.close()
                
            except Exception as kb_error:
                logger.warning(f"Could not fetch LLM response statistics from KnowledgeDocuments: {kb_error}")
                # Continue with default values if KnowledgeDocuments is not accessible

            return {
                'id': batch.id,
                'batch_number': batch.batch_number,
                'batch_name': batch.batch_name,
                'description': batch.description,
                'status': batch.status,
                'created_at': batch.created_at.isoformat() if batch.created_at else None,
                'completed_at': batch.completed_at.isoformat() if batch.completed_at else None,
                'total_documents': document_count,
                'total_responses': total_responses,
                'status_counts': status_counts,
                'completion_percentage': completion_percentage
            }

        except Exception as e:
            logger.error(f"Error getting batch info {batch_id}: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def list_batches(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List recent batches with summary information - includes LLM response data from KnowledgeDocuments database

        Args:
            limit (int): Maximum number of batches to return

        Returns:
            list: List of batch summaries with completion data
        """
        session = Session()
        try:
            batches = session.query(Batch).order_by(Batch.created_at.desc()).limit(limit).all()

            # Get all batch IDs for bulk query
            batch_ids = [batch.id for batch in batches]
            
            # Get LLM response statistics from KnowledgeDocuments database
            batch_stats = {}
            try:
                if batch_ids:
                    import psycopg2
                    kb_conn = psycopg2.connect(
                        host="studio.local",
                        database="KnowledgeDocuments",
                        user="postgres",
                        password="prodogs03",
                        port=5432
                    )
                    kb_cursor = kb_conn.cursor()
                    
                    # Get total responses and completion counts for all batches in one query
                    kb_cursor.execute("""
                        SELECT 
                            batch_id,
                            COUNT(*) as total,
                            SUM(CASE WHEN status IN ('S', 'F') THEN 1 ELSE 0 END) as completed
                        FROM llm_responses 
                        WHERE batch_id = ANY(%s)
                        GROUP BY batch_id
                    """, (batch_ids,))
                    
                    for batch_id, total, completed in kb_cursor.fetchall():
                        completion_percentage = round((completed / total * 100)) if total > 0 else 0
                        batch_stats[batch_id] = {
                            'total_responses': total,
                            'completion_percentage': completion_percentage
                        }
                    
                    kb_cursor.close()
                    kb_conn.close()
                    
            except Exception as kb_error:
                logger.warning(f"Could not fetch LLM response statistics from KnowledgeDocuments: {kb_error}")

            batch_list = []
            for batch in batches:
                # Get document count for this batch
                document_count = session.query(Document).filter_by(batch_id=batch.id).count()

                # Get stats from our bulk query, or use defaults
                stats = batch_stats.get(batch.id, {'total_responses': 0, 'completion_percentage': 0})
                
                batch_list.append({
                    'id': batch.id,
                    'batch_number': batch.batch_number,
                    'batch_name': batch.batch_name,
                    'status': batch.status,
                    'created_at': batch.created_at.isoformat() if batch.created_at else None,
                    'total_documents': document_count,
                    'total_responses': stats['total_responses'],
                    'completion_percentage': stats['completion_percentage']
                })

            return batch_list

        except Exception as e:
            logger.error(f"Error listing batches: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_current_batch(self) -> Optional[Batch]:
        """
        Get the most recent batch that is still processing

        Returns:
            Batch: The current processing batch or None
        """
        session = Session()
        try:
            batch = session.query(Batch).filter(Batch.status.in_(['P', 'PA'])).order_by(Batch.created_at.desc()).first()
            return batch
        except Exception as e:
            logger.error(f"Error getting current batch: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def _check_and_update_batch_completion_status(self) -> None:
        """
        Check if any batches have all their tasks completed and update batch status accordingly
        This method queries the KnowledgeDocuments database to check task completion
        """
        try:
            import psycopg2
            import json
            
            # Connect to both databases
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            doc_eval_session = Session()
            
            # Get all batches that are currently ANALYZING or PROCESSING
            analyzing_batches = doc_eval_session.query(Batch).filter(
                Batch.status.in_(['ANALYZING', 'PROCESSING'])
            ).all()
            
            for batch in analyzing_batches:
                # Get all documents in this batch
                batch_documents = doc_eval_session.query(Document).filter(
                    Document.batch_id == batch.id
                ).all()
                
                if not batch_documents:
                    continue
                
                # Create mapping from doc_eval document IDs to KnowledgeDocuments doc IDs
                kb_doc_ids = []
                logger.info(f"🔍 Looking for documents for batch {batch.id} ({len(batch_documents)} documents)")
                
                for doc in batch_documents:
                    # The doc_id in KnowledgeDocuments follows pattern: batch_{batch_id}_doc_{doc_id}
                    kb_doc_id_pattern = f"batch_{batch.id}_doc_{doc.id}"
                    logger.info(f"   Searching for document pattern: {kb_doc_id_pattern}")
                    
                    # Find the actual doc_id in KnowledgeDocuments database
                    kb_cursor.execute(
                        "SELECT id FROM docs WHERE document_id = %s",
                        (kb_doc_id_pattern,)
                    )
                    result = kb_cursor.fetchone()
                    if result:
                        kb_doc_ids.append(result[0])
                        logger.info(f"   ✅ Found KB doc_id: {result[0]} for pattern: {kb_doc_id_pattern}")
                    else:
                        logger.warning(f"   ❌ No KB document found for pattern: {kb_doc_id_pattern}")
                
                logger.info(f"🔍 Found {len(kb_doc_ids)} KnowledgeDocuments doc IDs: {kb_doc_ids}")
                
                if not kb_doc_ids:
                    logger.warning(f"No KnowledgeDocuments found for batch {batch.id}")
                    continue
                
                # Check llm_responses for all documents in this batch
                logger.info(f"🔍 Querying llm_responses for KB doc IDs: {kb_doc_ids}")
                
                kb_cursor.execute("""
                    SELECT 
                        COUNT(*) as total_responses,
                        COUNT(CASE WHEN status = 'S' THEN 1 END) as completed_responses,
                        COUNT(CASE WHEN status = 'F' THEN 1 END) as failed_responses,
                        COUNT(CASE WHEN status = 'QUEUED' THEN 1 END) as queued_responses
                    FROM llm_responses 
                    WHERE document_id = ANY(%s)
                """, (kb_doc_ids,))
                
                # Also check what llm_responses actually exist for debugging
                kb_cursor.execute("""
                    SELECT document_id, status, task_id
                    FROM llm_responses 
                    WHERE document_id = ANY(%s)
                """, (kb_doc_ids,))
                actual_responses = kb_cursor.fetchall()
                logger.info(f"🔍 Actual llm_responses found: {actual_responses}")
                
                # Back to the count query
                kb_cursor.execute("""
                    SELECT 
                        COUNT(*) as total_responses,
                        COUNT(CASE WHEN status = 'S' THEN 1 END) as completed_responses,
                        COUNT(CASE WHEN status = 'F' THEN 1 END) as failed_responses,
                        COUNT(CASE WHEN status = 'QUEUED' THEN 1 END) as queued_responses
                    FROM llm_responses 
                    WHERE document_id = ANY(%s)
                """, (kb_doc_ids,))
                
                result = kb_cursor.fetchone()
                if not result:
                    continue
                
                total_responses, completed_responses, failed_responses, queued_responses = result
                finished_responses = completed_responses + failed_responses
                
                logger.info(f"📊 Batch {batch.id} progress: {finished_responses}/{total_responses} responses finished ({completed_responses} success, {failed_responses} failed, {queued_responses} queued)")
                
                # Check if all tasks are complete (no more QUEUED tasks)
                if queued_responses == 0 and total_responses > 0:
                    # All tasks are finished, update batch status
                    batch.status = 'COMPLETED'
                    batch.completed_at = func.now()
                    batch.processed_documents = len(batch_documents)
                    
                    doc_eval_session.commit()
                    
                    logger.info(f"🎉 Batch {batch.id} (#{batch.batch_number} - '{batch.batch_name}') marked as COMPLETED!")
                    logger.info(f"   📊 Final results: {completed_responses} successful, {failed_responses} failed out of {total_responses} total responses")
            
            kb_cursor.close()
            kb_conn.close()
            doc_eval_session.close()
            
        except Exception as e:
            logger.error(f"❌ Error checking batch completion status: {e}", exc_info=True)

    def _start_task_polling(self, task_id: str, doc_id: int, connection_id: int, prompt_id: int, connection_details: dict) -> None:
        """
        Start background polling for a specific task to check completion status
        
        Args:
            task_id: The task ID returned by RAG API
            doc_id: Document ID in KnowledgeDocuments database
            connection_id: Connection ID used for the task
            prompt_id: Prompt ID used for the task
            connection_details: Complete connection configuration
        """
        import threading
        import time
        import requests
        import json
        import psycopg2
        
        def poll_task():
            """Background polling function that runs in a separate thread"""
            
            max_attempts = 180  # 30 minutes with 10-second intervals
            attempt = 0
            
            logger.info(f"🔄 Starting background polling for task {task_id}")
            
            while attempt < max_attempts:
                try:
                    time.sleep(10)  # Poll every 10 seconds
                    attempt += 1
                    
                    # Check task status via RAG API
                    response = requests.get(
                        f"http://localhost:7001/analyze_status/{task_id}",
                        timeout=30
                    )
                    
                    if response.status_code == 200:
                        status_data = response.json()
                        task_status = status_data.get('status', 'unknown')
                        
                        logger.info(f"📊 Task {task_id} status: {task_status} (attempt {attempt}/{max_attempts})")
                        
                        # Debug: Log the full response structure to understand the data format
                        logger.info(f"🔍 Full response data for task {task_id}: {json.dumps(status_data, indent=2)}")
                        
                        if task_status in ['completed', 'success', 'failed']:
                            # Task is finished, update llm_responses
                            try:
                                kb_conn = psycopg2.connect(
                                    host="studio.local",
                                    database="KnowledgeDocuments", 
                                    user="postgres",
                                    password="prodogs03",
                                    port=5432
                                )
                                kb_cursor = kb_conn.cursor()
                                
                                # Initialize variables that might be used in both success and failure cases
                                response_time_ms = None
                                tokens_per_second = None
                                
                                if task_status in ['completed', 'success']:
                                    # Extract data from the response - try multiple possible structures
                                    analysis_data = status_data.get('data', {})
                                    result_data = status_data.get('result', {})
                                    task_result = status_data.get('task_result', {})
                                    
                                    # Handle results - array of LLMPromptResponse objects per OpenAPI spec
                                    results_raw = status_data.get('results', [])
                                    if isinstance(results_raw, list) and results_raw:
                                        # Get first result for primary response
                                        results_data = results_raw[0] if isinstance(results_raw[0], dict) else {}
                                        # Aggregate token metrics from all results
                                        total_input_tokens = 0
                                        total_output_tokens = 0
                                        total_time_taken = 0.0
                                        for result in results_raw:
                                            if isinstance(result, dict):
                                                if result.get('input_tokens'):
                                                    total_input_tokens += result.get('input_tokens', 0)
                                                if result.get('output_tokens'):
                                                    total_output_tokens += result.get('output_tokens', 0)
                                                if result.get('time_taken_seconds'):
                                                    total_time_taken += result.get('time_taken_seconds', 0)
                                    else:
                                        results_data = {}
                                        total_input_tokens = 0
                                        total_output_tokens = 0
                                        total_time_taken = 0.0
                                    
                                    # Handle scoring_result - could be dict or list
                                    scoring_raw = status_data.get('scoring_result', {})
                                    if isinstance(scoring_raw, list) and scoring_raw:
                                        scoring_data = scoring_raw[0] if isinstance(scoring_raw[0], dict) else {}
                                    elif isinstance(scoring_raw, dict):
                                        scoring_data = scoring_raw
                                    else:
                                        scoring_data = {}
                                    
                                    # Debug: Show what data structures we found
                                    logger.info(f"🔍 Data structures found for task {task_id}:")
                                    logger.info(f"   status_data keys: {list(status_data.keys())}")
                                    logger.info(f"   analysis_data keys: {list(analysis_data.keys()) if isinstance(analysis_data, dict) and analysis_data else 'None'}")
                                    logger.info(f"   result_data keys: {list(result_data.keys()) if isinstance(result_data, dict) and result_data else 'None'}")
                                    logger.info(f"   task_result keys: {list(task_result.keys()) if isinstance(task_result, dict) and task_result else 'None'}")
                                    logger.info(f"   results_data keys: {list(results_data.keys()) if isinstance(results_data, dict) and results_data else 'None'}")
                                    logger.info(f"   scoring_data keys: {list(scoring_data.keys()) if isinstance(scoring_data, dict) and scoring_data else 'None'}")
                                    logger.info(f"   results_raw type: {type(results_raw)} - {results_raw if not isinstance(results_raw, (dict, list)) or len(str(results_raw)) < 200 else f'{type(results_raw)} with {len(results_raw)} items'}")
                                    logger.info(f"   scoring_raw type: {type(scoring_raw)} - {scoring_raw if not isinstance(scoring_raw, (dict, list)) or len(str(scoring_raw)) < 200 else f'{type(scoring_raw)} with {len(scoring_raw)} items'}")
                                    
                                    # Log scoring_result details specifically
                                    if scoring_data:
                                        logger.info(f"   📊 scoring_result details: overall_score={scoring_data.get('overall_score')}, confidence={scoring_data.get('confidence')}, provider={scoring_data.get('provider_name')}")
                                    
                                    # Try to get response_text from multiple possible locations
                                    response_text = (
                                        results_data.get('response_text') or
                                        results_data.get('response') or
                                        results_data.get('content') or
                                        results_data.get('text') or
                                        results_data.get('output') or
                                        results_data.get('analysis') or
                                        status_data.get('message') or
                                        analysis_data.get('response_text') or 
                                        result_data.get('response_text') or
                                        task_result.get('response_text') or
                                        status_data.get('response_text') or
                                        analysis_data.get('response') or
                                        result_data.get('response') or
                                        task_result.get('response') or
                                        status_data.get('response') or
                                        analysis_data.get('content') or
                                        result_data.get('content') or
                                        task_result.get('content') or
                                        status_data.get('content') or
                                        analysis_data.get('text') or
                                        result_data.get('text') or
                                        task_result.get('text') or
                                        status_data.get('text') or
                                        analysis_data.get('output') or
                                        result_data.get('output') or
                                        task_result.get('output') or
                                        status_data.get('output') or
                                        ''
                                    )
                                    
                                    # Store the complete response as JSON
                                    response_json = json.dumps(status_data) if status_data else None
                                    
                                    # Extract metrics from various possible locations
                                    overall_score = (
                                        scoring_data.get('overall_score') or
                                        scoring_data.get('score') or
                                        scoring_data.get('rating') or
                                        results_data.get('overall_score') or
                                        results_data.get('score') or
                                        results_data.get('rating') or
                                        analysis_data.get('overall_score') or
                                        result_data.get('overall_score') or
                                        task_result.get('overall_score') or
                                        status_data.get('overall_score') or
                                        analysis_data.get('score') or
                                        result_data.get('score') or
                                        task_result.get('score') or
                                        status_data.get('score') or
                                        analysis_data.get('rating') or
                                        result_data.get('rating') or
                                        task_result.get('rating') or
                                        status_data.get('rating')
                                    )
                                    
                                    # Use aggregated token values if available from results array
                                    input_tokens = total_input_tokens if total_input_tokens > 0 else (
                                        results_data.get('input_tokens') or
                                        results_data.get('tokens_in') or
                                        results_data.get('prompt_tokens') or
                                        analysis_data.get('input_tokens') or
                                        result_data.get('input_tokens') or
                                        task_result.get('input_tokens') or
                                        status_data.get('input_tokens') or
                                        analysis_data.get('tokens_in') or
                                        result_data.get('tokens_in') or
                                        task_result.get('tokens_in') or
                                        status_data.get('tokens_in') or
                                        analysis_data.get('prompt_tokens') or
                                        result_data.get('prompt_tokens') or
                                        task_result.get('prompt_tokens') or
                                        status_data.get('prompt_tokens')
                                    )
                                    
                                    output_tokens = total_output_tokens if total_output_tokens > 0 else (
                                        results_data.get('output_tokens') or
                                        results_data.get('tokens_out') or
                                        results_data.get('completion_tokens') or
                                        analysis_data.get('output_tokens') or
                                        result_data.get('output_tokens') or
                                        task_result.get('output_tokens') or
                                        status_data.get('output_tokens') or
                                        analysis_data.get('tokens_out') or
                                        result_data.get('tokens_out') or
                                        task_result.get('tokens_out') or
                                        status_data.get('tokens_out') or
                                        analysis_data.get('completion_tokens') or
                                        result_data.get('completion_tokens') or
                                        task_result.get('completion_tokens') or
                                        status_data.get('completion_tokens')
                                    )
                                    
                                    time_taken = total_time_taken if total_time_taken > 0 else (
                                        results_data.get('time_taken_seconds') or
                                        results_data.get('processing_time') or
                                        results_data.get('duration') or
                                        results_data.get('elapsed_time') or
                                        results_data.get('execution_time') or
                                        analysis_data.get('time_taken_seconds') or
                                        result_data.get('time_taken_seconds') or
                                        task_result.get('time_taken_seconds') or
                                        status_data.get('time_taken_seconds') or
                                        analysis_data.get('processing_time') or
                                        result_data.get('processing_time') or
                                        task_result.get('processing_time') or
                                        status_data.get('processing_time') or
                                        analysis_data.get('duration') or
                                        result_data.get('duration') or
                                        task_result.get('duration') or
                                        status_data.get('duration') or
                                        analysis_data.get('elapsed_time') or
                                        result_data.get('elapsed_time') or
                                        task_result.get('elapsed_time') or
                                        status_data.get('elapsed_time') or
                                        analysis_data.get('execution_time') or
                                        result_data.get('execution_time') or
                                        task_result.get('execution_time') or
                                        status_data.get('execution_time')
                                    )
                                    
                                    # Add detailed debugging to see where values come from
                                    logger.info(f"📝 Raw extraction attempts for task {task_id}:")
                                    if response_text:
                                        for location in ['analysis_data', 'result_data', 'task_result', 'status_data']:
                                            data = locals()[location] if location in locals() else {}
                                            for field in ['response_text', 'response', 'content', 'text', 'output']:
                                                if data.get(field):
                                                    logger.info(f"   Found response_text in {location}.{field}")
                                                    break
                                    
                                    if overall_score:
                                        for location in ['analysis_data', 'result_data', 'task_result', 'status_data']:
                                            data = locals()[location] if location in locals() else {}
                                            for field in ['overall_score', 'score', 'rating']:
                                                if data.get(field):
                                                    logger.info(f"   Found overall_score in {location}.{field}: {data.get(field)}")
                                                    break
                                    
                                    logger.info(f"📝 Final extracted data for task {task_id}:")
                                    logger.info(f"   Response text length: {len(response_text) if response_text else 0}")
                                    logger.info(f"   Response text preview: {response_text[:100] if response_text else 'None'}...")
                                    logger.info(f"   Overall score: {overall_score}")
                                    logger.info(f"   Input tokens: {input_tokens}")
                                    logger.info(f"   Output tokens: {output_tokens}")
                                    logger.info(f"   Time taken: {time_taken} seconds")
                                    logger.info(f"   Response time: {response_time_ms} ms")
                                    logger.info(f"   Tokens per second: {tokens_per_second}")
                                    logger.info(f"   Response JSON length: {len(response_json) if response_json else 0}")
                                    
                                    # Convert time to float if it's a string
                                    if time_taken and isinstance(time_taken, str):
                                        try:
                                            time_taken = float(time_taken)
                                        except ValueError:
                                            logger.warning(f"Could not convert time_taken '{time_taken}' to float")
                                            time_taken = None
                                    
                                    # Convert score to float if it's a string
                                    if overall_score and isinstance(overall_score, str):
                                        try:
                                            overall_score = float(overall_score)
                                        except ValueError:
                                            logger.warning(f"Could not convert overall_score '{overall_score}' to float")
                                            overall_score = None
                                    
                                    # Convert tokens to integers if they're strings
                                    if input_tokens and isinstance(input_tokens, str):
                                        try:
                                            input_tokens = int(input_tokens)
                                        except ValueError:
                                            logger.warning(f"Could not convert input_tokens '{input_tokens}' to int")
                                            input_tokens = None
                                    
                                    if output_tokens and isinstance(output_tokens, str):
                                        try:
                                            output_tokens = int(output_tokens)
                                        except ValueError:
                                            logger.warning(f"Could not convert output_tokens '{output_tokens}' to int")
                                            output_tokens = None
                                    
                                    # Calculate additional metrics
                                    response_time_ms = int(time_taken * 1000) if time_taken else None
                                    
                                    # Calculate tokens per second if we have both tokens and time
                                    tokens_per_second = None
                                    if time_taken and time_taken > 0:
                                        total_tokens = 0
                                        if input_tokens:
                                            total_tokens += input_tokens
                                        if output_tokens:
                                            total_tokens += output_tokens
                                        if total_tokens > 0:
                                            tokens_per_second = round(total_tokens / time_taken, 2)
                                    
                                    # Update llm_responses with successful completion - include ALL available fields
                                    logger.info(f"🔄 Updating llm_responses for task_id: {task_id}")
                                    
                                    update_result = kb_cursor.execute("""
                                        UPDATE llm_responses 
                                        SET status = %s, 
                                            completed_processing_at = NOW(),
                                            response_text = %s,
                                            response_json = %s,
                                            overall_score = %s,
                                            input_tokens = %s,
                                            output_tokens = %s,
                                            time_taken_seconds = %s,
                                            response_time_ms = %s,
                                            tokens_per_second = %s,
                                            timestamp = NOW()
                                        WHERE task_id = %s
                                    """, (
                                        'S',  # Success
                                        response_text,
                                        response_json,
                                        overall_score,
                                        input_tokens,
                                        output_tokens,
                                        time_taken,
                                        response_time_ms,
                                        tokens_per_second,
                                        task_id
                                    ))
                                    
                                    # Check how many rows were affected
                                    rows_affected = kb_cursor.rowcount
                                    logger.info(f"🔄 UPDATE affected {rows_affected} rows for task_id: {task_id}")
                                    
                                    if rows_affected == 0:
                                        logger.error(f"❌ No rows updated for task_id: {task_id} - checking if record exists")
                                        # Check if the record exists
                                        kb_cursor.execute("SELECT id, status FROM llm_responses WHERE task_id = %s", (task_id,))
                                        existing_record = kb_cursor.fetchone()
                                        if existing_record:
                                            logger.error(f"❌ Record exists but wasn't updated: {existing_record}")
                                        else:
                                            logger.error(f"❌ No record found with task_id: {task_id}")
                                    
                                    # COMMIT the transaction BEFORE checking batch completion
                                    kb_conn.commit()
                                    
                                    logger.info(f"✅ Task {task_id} completed successfully and llm_responses updated")
                                    
                                    # Check if all tasks for this batch are now complete
                                    # Add a small delay to ensure database transaction is committed
                                    time.sleep(0.1)
                                    self._check_and_update_batch_completion_status()
                                    
                                    kb_cursor.close()
                                    kb_conn.close()
                                    
                                    # Task is finished, exit polling loop
                                    break
                                    
                                else:  # failed
                                    # Extract error information from various possible locations
                                    error_message = (
                                        status_data.get('error') or
                                        status_data.get('error_message') or
                                        status_data.get('message') or
                                        status_data.get('data', {}).get('error') or
                                        status_data.get('result', {}).get('error') or
                                        'Task failed'
                                    )
                                    
                                    # Try to extract any partial data even from failed tasks
                                    analysis_data = status_data.get('data', {})
                                    result_data = status_data.get('result', {})
                                    
                                    # Store the complete response as JSON even for failures (useful for debugging)
                                    response_json = json.dumps(status_data) if status_data else None
                                    
                                    # Try to get timing info even from failed tasks
                                    time_taken = (
                                        analysis_data.get('time_taken_seconds') or
                                        result_data.get('time_taken_seconds') or
                                        status_data.get('time_taken_seconds') or
                                        analysis_data.get('processing_time') or
                                        result_data.get('processing_time') or
                                        status_data.get('processing_time') or
                                        analysis_data.get('duration') or
                                        result_data.get('duration') or
                                        status_data.get('duration')
                                    )
                                    
                                    # Convert time to float if it's a string
                                    if time_taken and isinstance(time_taken, str):
                                        try:
                                            time_taken = float(time_taken)
                                        except ValueError:
                                            time_taken = None
                                    
                                    # Calculate response time in milliseconds
                                    response_time_ms = int(time_taken * 1000) if time_taken else None
                                    
                                    logger.info(f"📝 Extracted failure data for task {task_id}:")
                                    logger.info(f"   Error message: {error_message}")
                                    logger.info(f"   Time taken: {time_taken} seconds")
                                    logger.info(f"   Response time: {response_time_ms} ms")
                                    logger.info(f"   Response JSON length: {len(response_json) if response_json else 0}")
                                    
                                    # Update llm_responses with failure - include all available data
                                    kb_cursor.execute("""
                                        UPDATE llm_responses 
                                        SET status = %s,
                                            completed_processing_at = NOW(),
                                            error_message = %s,
                                            response_json = %s,
                                            time_taken_seconds = %s,
                                            response_time_ms = %s,
                                            timestamp = NOW()
                                        WHERE task_id = %s
                                    """, (
                                        'F',  # Failed
                                        error_message,
                                        response_json,
                                        time_taken,
                                        response_time_ms,
                                        task_id
                                    ))
                                    
                                    logger.error(f"❌ Task {task_id} failed: {error_message}")
                                
                                    # COMMIT the transaction BEFORE checking batch completion
                                    kb_conn.commit()
                                    
                                    # Check if all tasks for this batch are now complete (including failures)
                                    # Add a small delay to ensure database transaction is committed
                                    time.sleep(0.1)
                                    self._check_and_update_batch_completion_status()
                                
                                kb_cursor.close()
                                kb_conn.close()
                                
                                # Task is finished, exit polling loop
                                break
                                
                            except Exception as e:
                                logger.error(f"❌ Error updating llm_responses for task {task_id}: {e}")
                                
                        elif task_status == 'processing':
                            # Task is still processing, continue polling
                            continue
                        else:
                            # Unknown status, continue polling but log warning
                            logger.warning(f"⚠️ Unknown task status for {task_id}: {task_status}")
                            continue
                            
                    elif response.status_code == 404:
                        # Task not found - it might have been cleaned up
                        logger.warning(f"⚠️ Task {task_id} not found (404) - may have been cleaned up")
                        break
                    else:
                        logger.warning(f"⚠️ Unexpected status code {response.status_code} for task {task_id}")
                        
                except requests.exceptions.RequestException as e:
                    logger.warning(f"⚠️ Network error polling task {task_id}: {e}")
                    # Continue polling despite network errors
                    continue
                except Exception as e:
                    logger.error(f"❌ Unexpected error polling task {task_id}: {e}")
                    continue
            
            # If we exit the loop without completing, mark as timeout
            if attempt >= max_attempts:
                logger.error(f"❌ Task {task_id} polling timed out after {max_attempts} attempts")
                try:
                    kb_conn = psycopg2.connect(
                        host="studio.local",
                        database="KnowledgeDocuments",
                        user="postgres", 
                        password="prodogs03",
                        port=5432
                    )
                    kb_cursor = kb_conn.cursor()
                    
                    kb_cursor.execute("""
                        UPDATE llm_responses 
                        SET status = %s,
                            error_message = %s
                        WHERE task_id = %s AND status = 'QUEUED'
                    """, (
                        'F',  # Failed
                        f'Polling timeout after {max_attempts * 10} seconds',
                        task_id
                    ))
                    
                    kb_conn.commit()
                    kb_cursor.close()
                    kb_conn.close()
                    
                except Exception as e:
                    logger.error(f"❌ Error updating llm_responses for timed out task {task_id}: {e}")
        
        # Start polling in background thread
        polling_thread = threading.Thread(target=poll_task, daemon=True)
        polling_thread.start()
        logger.info(f"🚀 Started background polling thread for task {task_id}")

    def save_batch(self, folder_ids: List[int], connection_ids: List[int], prompt_ids: List[int],
                   batch_name: Optional[str] = None, description: Optional[str] = None,
                   meta_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Save batch configuration without staging (creates batch in SAVED status)"""
        logger.info(f"save_batch called for '{batch_name}' - creating batch configuration")
        
        try:
            session = Session()
            
            try:
                # Get the next batch number
                max_batch_number = session.query(func.max(Batch.batch_number)).scalar()
                next_batch_number = (max_batch_number or 0) + 1

                # Create configuration snapshot
                config_snapshot = self._create_config_snapshot(folder_ids)
                
                # Add connection and prompt IDs to config
                config_snapshot['connection_ids'] = connection_ids
                config_snapshot['prompt_ids'] = prompt_ids

                # Create the batch with SAVED status
                batch = Batch(
                    batch_number=next_batch_number,
                    batch_name=batch_name,
                    description=description or f"Saved batch with {len(folder_ids)} folders, {len(connection_ids)} connections, {len(prompt_ids)} prompts",
                    folder_ids=folder_ids,
                    meta_data=meta_data,
                    config_snapshot=config_snapshot,
                    status='SAVED',  # Saved but not staged
                    total_documents=0,
                    processed_documents=0
                )

                session.add(batch)
                session.commit()

                logger.info(f"✅ Created batch #{next_batch_number} - {batch_name} with SAVED status")

                result = {
                    'success': True,
                    'batch_id': batch.id,
                    'batch_number': batch.batch_number,
                    'batch_name': batch.batch_name,
                    'status': batch.status,
                    'message': f'Batch #{batch.batch_number} saved successfully'
                }

                return result

            except Exception as e:
                session.rollback()
                logger.error(f"Error saving batch: {e}", exc_info=True)
                return {
                    'success': False,
                    'error': str(e)
                }
            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error in save_batch: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e)
            }

    def stage_batch(self, folder_ids: List[int], connection_ids: List[int], prompt_ids: List[int],
                    batch_name: Optional[str] = None, description: Optional[str] = None,
                    meta_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Create and stage a new batch (creates batch in STAGING status and prepares documents)"""
        logger.info(f"stage_batch called for '{batch_name}' with {len(folder_ids)} folders, {len(connection_ids)} connections, {len(prompt_ids)} prompts")
        
        try:
            session = Session()
            
            try:
                # Get the next batch number
                max_batch_number = session.query(func.max(Batch.batch_number)).scalar()
                next_batch_number = (max_batch_number or 0) + 1

                # Create configuration snapshot
                config_snapshot = self._create_config_snapshot(folder_ids)
                
                # Add connection and prompt IDs to config
                config_snapshot['connection_ids'] = connection_ids
                config_snapshot['prompt_ids'] = prompt_ids

                # Create the batch
                batch = Batch(
                    batch_number=next_batch_number,
                    batch_name=batch_name,
                    description=description or f"Staged batch with {len(folder_ids)} folders, {len(connection_ids)} connections, {len(prompt_ids)} prompts",
                    folder_ids=folder_ids,
                    meta_data=meta_data,
                    config_snapshot=config_snapshot,
                    status='STAGING',
                    total_documents=0,
                    processed_documents=0
                )

                session.add(batch)
                session.commit()
                batch_id = batch.id
                
                logger.info(f"Created batch #{next_batch_number} - {batch_name} with STAGING status")
                
                # Assign documents to the batch
                total_assigned = 0
                for folder_id in folder_ids:
                    # Get unassigned documents from this folder
                    unassigned_docs = session.query(Document).filter(
                        Document.folder_id == folder_id,
                        Document.batch_id.is_(None),
                        Document.valid == 'Y'
                    ).all()

                    # Assign these documents to the batch
                    for doc in unassigned_docs:
                        doc.batch_id = batch_id
                        total_assigned += 1

                    logger.info(f"Assigned {len(unassigned_docs)} documents from folder {folder_id} to batch {batch_id}")

                # Update batch total_documents count
                batch.total_documents = total_assigned
                session.commit()
                
                # Perform actual staging to KnowledgeDocuments database
                encoding_service = DocumentEncodingService()
                staging_result = self._perform_staging(session, batch_id, folder_ids, connection_ids, prompt_ids, encoding_service)
                
                if staging_result['success']:
                    # Update batch status to STAGED
                    batch.status = 'STAGED'
                    session.commit()
                    
                    logger.info(f"Successfully staged batch {batch_id}: {staging_result['total_documents']} documents, {staging_result['total_responses']} responses")
                    
                    return {
                        'success': True,
                        'batch_id': batch_id,
                        'batch_number': next_batch_number,
                        'batch_name': batch_name,
                        'status': 'STAGED',
                        'total_documents': staging_result['total_documents'],
                        'total_responses': staging_result['total_responses'],
                        'message': f'Batch #{next_batch_number} staged successfully with {staging_result["total_documents"]} documents'
                    }
                else:
                    # Update batch status to FAILED_STAGING
                    batch.status = 'FAILED_STAGING'
                    session.commit()
                    
                    logger.error(f"Staging failed for batch {batch_id}: {staging_result.get('error', 'Unknown error')}")
                    
                    return {
                        'success': False,
                        'batch_id': batch_id,
                        'batch_number': next_batch_number,
                        'status': 'FAILED_STAGING',
                        'error': staging_result.get('error', 'Staging failed'),
                        'message': f'Batch #{next_batch_number} staging failed'
                    }
                    
            except Exception as e:
                session.rollback()
                logger.error(f"Error in stage_batch: {e}", exc_info=True)
                return {
                    'success': False,
                    'error': str(e),
                    'message': 'Failed to stage batch'
                }
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error in stage_batch: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'message': 'Failed to stage batch'
            }

    def restage_batch(self, batch_id: int) -> Dict[str, Any]:
        """Restage an existing batch (prepare documents and update batch status)"""
        logger.info(f"restage_batch called for batch {batch_id}")

        try:
            session = Session()

            # Get the batch
            batch = session.query(Batch).filter(Batch.id == batch_id).first()
            if not batch:
                session.close()
                return {
                    'success': False,
                    'error': f'Batch {batch_id} not found'
                }

            # Get documents associated with this batch
            documents = session.query(Document).filter(Document.batch_id == batch_id).all()

            # If no documents are assigned to this batch yet, assign them from the batch's folders
            if not documents and batch.folder_ids:
                logger.info(f"No documents assigned to batch {batch_id} yet. Assigning documents from folders: {batch.folder_ids}")

                total_assigned = 0
                documents_assigned_in_loop = 0
                for folder_id in batch.folder_ids:
                    # First, try to get unassigned documents from this folder
                    unassigned_docs = session.query(Document).filter(
                        Document.folder_id == folder_id,
                        Document.batch_id.is_(None),
                        Document.valid == 'Y'  # Only assign valid documents
                    ).all()

                    # If no unassigned documents, check if this is a restaging operation
                    # and consider reassigning documents from the same folders
                    if not unassigned_docs:
                        logger.info(f"No unassigned documents in folder {folder_id}, checking for documents assigned to other batches")
                        # Log current batch_id for debugging
                        logger.info(f"Looking for documents in folder {folder_id} not assigned to batch {batch_id}")
                        from sqlalchemy import and_, or_
                        assigned_docs = session.query(Document).filter(
                            Document.folder_id == folder_id,
                            Document.batch_id.isnot(None),  # Has a batch_id
                            Document.batch_id != batch_id,  # But not this batch
                            Document.valid == 'Y'
                        ).all()
                        
                        if assigned_docs:
                            logger.info(f"Found {len(assigned_docs)} documents in folder {folder_id} assigned to other batches, reassigning to batch {batch_id}")
                            # Reassign these documents to the current batch
                            for doc in assigned_docs:
                                doc.batch_id = batch_id
                                total_assigned += 1
                        else:
                            # Check if there are ANY documents in this folder
                            all_docs = session.query(Document).filter(
                                Document.folder_id == folder_id
                            ).all()
                            logger.warning(f"No documents found in folder {folder_id} to assign. Total docs in folder: {len(all_docs)}")
                            if all_docs:
                                for doc in all_docs:
                                    logger.info(f"  Doc {doc.id}: batch_id={doc.batch_id}, valid={doc.valid}")
                    else:
                        # Assign unassigned documents to the batch
                        for doc in unassigned_docs:
                            doc.batch_id = batch_id
                            total_assigned += 1

                    logger.info(f"Total documents assigned from folder {folder_id} to batch {batch_id}: {total_assigned}")

                if total_assigned > 0:
                    # Update batch total_documents count
                    batch.total_documents = total_assigned
                    session.commit()
                    logger.info(f"Successfully assigned {total_assigned} documents to batch {batch_id}")

                    # Re-query to get the newly assigned documents
                    documents = session.query(Document).filter(Document.batch_id == batch_id).all()
                else:
                    session.close()
                    return {
                        'success': False,
                        'error': f'No valid documents found in folders {batch.folder_ids} for batch {batch_id}'
                    }

            if not documents:
                session.close()
                return {
                    'success': False,
                    'error': f'No documents found for batch {batch_id}'
                }

            # Update batch status to STAGING
            batch.status = 'STAGING'
            batch.updated_at = func.now()
            session.commit()

            # Get connection and prompt IDs from batch config
            connection_ids = []
            prompt_ids = []
            
            if batch.config_snapshot:
                # Extract connection IDs
                connection_ids = batch.config_snapshot.get('connection_ids', [])
                if not connection_ids:
                    # Fallback: extract from connections array
                    connections = batch.config_snapshot.get('connections', [])
                    connection_ids = [conn['id'] for conn in connections if 'id' in conn]
                
                # Extract prompt IDs
                prompt_ids = batch.config_snapshot.get('prompt_ids', [])
                if not prompt_ids:
                    # Fallback: extract from prompts array
                    prompts = batch.config_snapshot.get('prompts', [])
                    prompt_ids = [prompt['id'] for prompt in prompts if 'id' in prompt]
            
            logger.info(f"Extracted from config: {len(connection_ids)} connections, {len(prompt_ids)} prompts")

            # Use _perform_staging to actually create llm_responses
            encoding_service = DocumentEncodingService()
            staging_result = self._perform_staging(
                session, 
                batch_id, 
                batch.folder_ids or [], 
                connection_ids, 
                prompt_ids, 
                encoding_service
            )

            # Update batch status based on staging result
            if staging_result['success']:
                batch.status = 'STAGED'
                final_status = 'STAGED'
                documents_prepared = staging_result['total_documents']
                responses_created = staging_result['total_responses']
                logger.info(f"Batch {batch_id} staging completed - {documents_prepared} documents, {responses_created} llm_responses created")
            else:
                batch.status = 'FAILED_STAGING'
                final_status = 'FAILED_STAGING'
                documents_prepared = 0
                responses_created = 0
                logger.warning(f"Batch {batch_id} staging failed: {staging_result.get('error', 'Unknown error')}")

            session.commit()
            session.close()

            return {
                'success': True,
                'batch_id': batch_id,
                'documents_prepared': documents_prepared,
                'total_documents': len(documents),
                'total_responses': responses_created,
                'status': final_status,
                'message': f'Batch staging completed - {documents_prepared}/{len(documents)} documents prepared, {responses_created} llm_responses created'
            }

        except Exception as e:
            if 'session' in locals():
                session.rollback()
                session.close()
            logger.error(f"Error in restage_batch for batch {batch_id}: {e}", exc_info=True)
            return {
                'success': False,
                'error': str(e),
                'batch_id': batch_id
            }

    def _perform_staging(self, session, batch_id: int, folder_ids: List[int],
                        connection_ids: List[int], prompt_ids: List[int],
                        encoding_service) -> Dict[str, Any]:
        """Perform staging - prepare documents and create entries in KnowledgeDocuments"""
        logger.info(f"Starting staging for batch {batch_id}")
        logger.info(f"Connection IDs: {connection_ids}")
        logger.info(f"Prompt IDs: {prompt_ids}")
        logger.info(f"Folder IDs: {folder_ids}")
        
        try:
            # First, find and assign unassigned documents from the specified folders
            logger.info(f"Looking for unassigned documents in folders: {folder_ids}")
            
            unassigned_documents = session.query(Document).filter(
                Document.folder_id.in_(folder_ids),
                Document.batch_id.is_(None),  # Unassigned documents
                Document.valid == 'Y'  # Only valid documents
            ).all()
            
            logger.info(f"Found {len(unassigned_documents)} unassigned documents to assign to batch {batch_id}")
            
            # Assign these documents to the batch
            for doc in unassigned_documents:
                doc.batch_id = batch_id
                logger.info(f"Assigned document {doc.id} ({doc.filename}) to batch {batch_id}")
            
            session.commit()
            
            # Now get all documents for this batch (including newly assigned ones)
            documents = session.query(Document).filter(
                Document.batch_id == batch_id
            ).all()
            
            logger.info(f"Found {len(documents)} total documents for batch {batch_id}")
            
            if not documents:
                logger.warning(f"No documents found for batch {batch_id} after assignment")
                return {
                    'success': False,
                    'error': 'No documents found for batch',
                    'total_documents': 0,
                    'total_responses': 0
                }
            
            # Connect to KnowledgeDocuments database
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            documents_staged = 0
            responses_created = 0
            
            logger.info(f"Starting to process {len(documents)} documents")
            
            for doc in documents:
                logger.info(f"Processing document: {doc.filename} (ID: {doc.id}, Path: {doc.filepath})")
                try:
                    # Check if file exists
                    if not os.path.exists(doc.filepath):
                        logger.warning(f"File not found: {doc.filepath}")
                        continue
                    
                    # Read and encode file
                    with open(doc.filepath, 'rb') as f:
                        file_content = f.read()
                    
                    # Encode to base64
                    encoded_content = base64.b64encode(file_content).decode('utf-8')
                    
                    # Clean encoded content - ensure it's valid base64
                    encoded_content = encoded_content.strip()
                    if len(encoded_content) % 4 != 0:
                        encoded_content += '=' * (4 - len(encoded_content) % 4)
                    
                    # Create document ID
                    doc_id = f"batch_{batch_id}_doc_{doc.id}"
                    
                    # Check if document already exists
                    kb_cursor.execute("SELECT id FROM docs WHERE document_id = %s", (doc_id,))
                    existing = kb_cursor.fetchone()
                    
                    if existing:
                        # Update existing document
                        kb_cursor.execute("""
                            UPDATE docs 
                            SET content = %s, file_size = %s, created_at = NOW()
                            WHERE document_id = %s
                            RETURNING id
                        """, (encoded_content, len(file_content), doc_id))
                        kb_doc_id = kb_cursor.fetchone()[0]
                        logger.info(f"Updated existing document in KnowledgeDocuments: {kb_doc_id}")
                    else:
                        # Insert new document
                        kb_cursor.execute("""
                            INSERT INTO docs (document_id, content, content_type, doc_type, file_size, encoding, created_at)
                            VALUES (%s, %s, %s, %s, %s, %s, NOW())
                            RETURNING id
                        """, (
                            doc_id,
                            encoded_content,
                            'text/plain',
                            os.path.splitext(doc.filename)[1][1:] if '.' in doc.filename else 'txt',
                            len(file_content),
                            'base64'
                        ))
                        kb_doc_id = kb_cursor.fetchone()[0]
                        logger.info(f"Created new document in KnowledgeDocuments: {kb_doc_id}")
                    kb_conn.commit()  # Commit after each document to avoid transaction issues
                    documents_staged += 1
                    
                    # Create LLM response entries for each connection/prompt combination
                    logger.info(f"Creating LLM responses for document {kb_doc_id} with {len(connection_ids)} connections and {len(prompt_ids)} prompts")
                    for conn_id in connection_ids:
                        # Get connection details from database
                        connection = session.query(Connection).filter_by(id=conn_id).first()
                        if not connection:
                            logger.warning(f"Connection {conn_id} not found in database")
                            continue
                            
                        # Get model and provider details for LLM config
                        model_name = 'default'
                        provider_type = 'ollama'
                        
                        if connection.model_id:
                            model = session.query(Model).filter_by(id=connection.model_id).first()
                            if model:
                                model_name = model.display_name
                        
                        if connection.provider_id:
                            provider = session.query(LlmProvider).filter_by(id=connection.provider_id).first()
                            if provider:
                                provider_type = provider.provider_type
                            
                        conn_details = {
                            'id': connection.id,
                            'name': connection.name,
                            'provider_id': connection.provider_id,
                            'model_id': connection.model_id,
                            'model_name': model_name,
                            'provider_type': provider_type,
                            'api_key': connection.api_key,
                            'base_url': connection.base_url,
                            'port_no': connection.port_no,
                            'connection_config': connection.connection_config
                        }
                        
                        for prompt_id in prompt_ids:
                            try:
                                logger.info(f"Inserting llm_response: doc_id={kb_doc_id}, prompt_id={prompt_id}, conn_id={conn_id}, batch_id={batch_id}")
                                kb_cursor.execute("""
                                    INSERT INTO llm_responses 
                                    (document_id, prompt_id, connection_id, connection_details, 
                                     status, created_at, batch_id)
                                    VALUES (%s, %s, %s, %s, %s, NOW(), %s)
                                    RETURNING id
                                """, (
                                    kb_doc_id,
                                    prompt_id,
                                    conn_id,
                                    json.dumps(conn_details),
                                    'QUEUED',
                                    batch_id
                                ))
                                result = kb_cursor.fetchone()
                                if result:
                                    kb_conn.commit()  # Commit each llm_response individually
                                    responses_created += 1
                                    logger.info(f"Created llm_response with id: {result[0]}")
                                else:
                                    kb_conn.rollback()  # Rollback if insert failed
                                    logger.warning(f"llm_response insert returned nothing")
                            except Exception as e:
                                kb_conn.rollback()  # Rollback on error
                                logger.error(f"Error inserting llm_response: {e}")
                                logger.error(f"Values: doc_id={kb_doc_id}, prompt_id={prompt_id}, conn_id={conn_id}, batch_id={batch_id}")
                    
                except Exception as e:
                    logger.error(f"Error staging document {doc.filename}: {e}")
                    continue
            
            # Close database connection
            kb_cursor.close()
            kb_conn.close()
            
            logger.info(f"Staging completed for batch {batch_id}: {documents_staged} documents, {responses_created} responses")
            
            return {
                'success': True,
                'total_documents': documents_staged,
                'total_responses': responses_created,
                'message': f'Successfully staged {documents_staged} documents'
            }
            
        except Exception as e:
            logger.error(f"Error in _perform_staging: {e}")
            return {
                'success': False,
                'error': str(e),
                'total_documents': 0,
                'total_responses': 0
            }

    def get_staging_status(self, batch_id: int) -> Dict[str, Any]:
        """Get staging status for a batch"""
        logger.info(f"get_staging_status called for batch {batch_id}")
        
        try:
            session = Session()
            batch = session.query(Batch).filter_by(id=batch_id).first()
            
            if not batch:
                session.close()
                return {
                    'batch_id': batch_id,
                    'status': 'NOT_FOUND',
                    'message': f'Batch {batch_id} not found'
                }
            
            session.close()
            
            return {
                'batch_id': batch_id,
                'status': batch.status,
                'total_documents': batch.total_documents,
                'message': f'Batch {batch_id} status: {batch.status}'
            }
            
        except Exception as e:
            logger.error(f"Error getting staging status for batch {batch_id}: {e}")
            return {
                'batch_id': batch_id,
                'status': 'ERROR',
                'error': str(e),
                'message': f'Error getting status for batch {batch_id}'
            }

    def get_batches_ready_for_processing(self) -> List[Dict[str, Any]]:
        """
        Get all batches with STAGED status or PROCESSING status with queued documents
        
        Returns:
            List of batch dictionaries with basic info
        """
        session = Session()
        try:
            # Query batches with STAGED or PROCESSING status
            batches = session.query(Batch).filter(
                Batch.status.in_(['STAGED', 'PROCESSING'])
            ).order_by(Batch.created_at.asc()).all()
            
            result = []
            for batch in batches:
                # For PROCESSING batches, check if they have queued documents
                if batch.status == 'PROCESSING':
                    try:
                        kb_conn = psycopg2.connect(
                            host="studio.local",
                            database="KnowledgeDocuments",
                            user="postgres",
                            password="prodogs03",
                            port=5432
                        )
                        kb_cursor = kb_conn.cursor()
                        
                        # Check if batch has queued documents
                        kb_cursor.execute("""
                            SELECT COUNT(*) 
                            FROM llm_responses 
                            WHERE batch_id = %s AND status = 'QUEUED'
                        """, (batch.id,))
                        
                        queued_count = kb_cursor.fetchone()[0]
                        kb_cursor.close()
                        kb_conn.close()
                        
                        # Skip PROCESSING batches with no queued documents
                        if queued_count == 0:
                            continue
                            
                    except Exception as e:
                        logger.error(f"Error checking queued documents for batch {batch.id}: {e}")
                        continue
                
                result.append({
                    'batch_id': batch.id,
                    'batch_number': batch.batch_number,
                    'batch_name': batch.batch_name,
                    'total_documents': batch.total_documents,
                    'processed_documents': batch.processed_documents,
                    'status': batch.status,
                    'created_at': batch.created_at.isoformat() if batch.created_at else None
                })
            
            logger.info(f"Found {len(result)} batches ready for processing")
            return result
            
        except Exception as e:
            logger.error(f"Error getting batches ready for processing: {e}")
            return []
        finally:
            session.close()

    def get_next_document_for_processing(self, batch_id: int) -> Optional[Dict[str, Any]]:
        """
        Get next QUEUED document from batch for processing
        
        Args:
            batch_id: ID of the batch to get document from
            
        Returns:
            Dict with document details and encoded content, or None if no documents available
        """
        session = Session()
        try:
            # Verify batch exists and is in correct state
            batch = session.query(Batch).filter_by(id=batch_id).first()
            if not batch:
                logger.error(f"Batch {batch_id} not found")
                return None
                
            if batch.status not in ['STAGED', 'PROCESSING']:
                logger.warning(f"Batch {batch_id} not in processable state: {batch.status}")
                return None
            
            # Update batch status if needed
            if batch.status == 'STAGED':
                batch.status = 'PROCESSING'
                batch.started_at = func.now()
                session.commit()
            
            # Connect to KnowledgeDocuments database to get next queued response
            try:
                kb_conn = psycopg2.connect(
                    host="studio.local",
                    database="KnowledgeDocuments",
                    user="postgres",
                    password="prodogs03",
                    port=5432
                )
                kb_cursor = kb_conn.cursor()
                
                # Get next QUEUED llm_response for this batch
                kb_cursor.execute("""
                    SELECT lr.id, lr.document_id, lr.prompt_id, lr.connection_id, 
                           lr.connection_details, d.document_id as kb_doc_id
                    FROM llm_responses lr
                    JOIN docs d ON lr.document_id = d.id
                    WHERE lr.batch_id = %s AND lr.status = 'QUEUED'
                    ORDER BY lr.created_at ASC
                    LIMIT 1
                    FOR UPDATE SKIP LOCKED
                """, (batch_id,))
                
                response_row = kb_cursor.fetchone()
                
                if not response_row:
                    kb_cursor.close()
                    kb_conn.close()
                    logger.info(f"No queued documents found for batch {batch_id}")
                    return None
                
                response_id, doc_id, prompt_id, connection_id, connection_details, kb_doc_id = response_row
                
                # Get document content from docs table
                kb_cursor.execute("""
                    SELECT content, content_type, doc_type, file_size
                    FROM docs
                    WHERE id = %s
                """, (doc_id,))
                
                doc_row = kb_cursor.fetchone()
                if not doc_row:
                    kb_cursor.close()
                    kb_conn.close()
                    logger.error(f"Document {doc_id} not found in KnowledgeDocuments")
                    return None
                
                content, content_type, doc_type, file_size = doc_row
                
                # Get prompt details from local database
                prompt = session.query(Prompt).filter_by(id=prompt_id).first()
                if not prompt:
                    kb_cursor.close()
                    kb_conn.close()
                    logger.error(f"Prompt {prompt_id} not found")
                    return None
                
                # Parse connection details
                if isinstance(connection_details, str):
                    connection_details = json.loads(connection_details)
                
                # Format the document data for processing
                result = {
                    'response_id': response_id,
                    'doc_id': doc_id,
                    'batch_id': batch_id,
                    'document_id': kb_doc_id,  # The unique document_id for RAG API
                    'encoded_content': content,  # Already base64 encoded
                    'content_type': content_type,
                    'doc_type': doc_type,
                    'file_size': file_size,
                    'prompt': {
                        'id': prompt_id,
                        'text': prompt.prompt_text,
                        'description': prompt.description
                    },
                    'llm_config': format_llm_config_for_rag_api(connection_details),
                    'connection_id': connection_id,
                    'connection_details': connection_details
                }
                
                kb_cursor.close()
                kb_conn.close()
                
                logger.info(f"Retrieved document {doc_id} for processing from batch {batch_id}")
                return result
                
            except Exception as e:
                logger.error(f"Error accessing KnowledgeDocuments database: {e}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting next document for processing: {e}")
            return None
        finally:
            session.close()

    def update_document_task(self, doc_id: int, task_id: str, status: str = 'PROCESSING') -> bool:
        """
        Update document with task_id when processing starts
        
        Args:
            doc_id: Document ID (from llm_responses)
            task_id: Task ID from RAG API
            status: New status (default: PROCESSING)
            
        Returns:
            bool: Success status
        """
        try:
            # Update in KnowledgeDocuments database
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            kb_cursor.execute("""
                UPDATE llm_responses 
                SET status = %s,
                    task_id = %s,
                    started_processing_at = NOW()
                WHERE id = %s
            """, (status, task_id, doc_id))
            
            kb_conn.commit()
            kb_cursor.close()
            kb_conn.close()
            
            logger.info(f"Updated document {doc_id} with task_id {task_id}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document task: {e}")
            return False

    def update_document_status(self, doc_id: int, status: str, response_data: Optional[Dict[str, Any]] = None) -> bool:
        """
        Update document status (COMPLETED/FAILED) with results
        
        Args:
            doc_id: Document ID (from llm_responses)
            status: Final status (COMPLETED/FAILED/TIMEOUT)
            response_data: Response data including text, tokens, etc.
            
        Returns:
            bool: Success status
        """
        session = Session()
        try:
            # Update in KnowledgeDocuments database
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Get batch_id for this document
            kb_cursor.execute("""
                SELECT batch_id FROM llm_responses WHERE id = %s
            """, (doc_id,))
            
            batch_row = kb_cursor.fetchone()
            if not batch_row:
                kb_cursor.close()
                kb_conn.close()
                logger.error(f"Document {doc_id} not found in llm_responses")
                return False
                
            batch_id = batch_row[0]
            
            # Update the llm_response record
            if status == 'COMPLETED' and response_data:
                kb_cursor.execute("""
                    UPDATE llm_responses 
                    SET status = %s,
                        response_text = %s,
                        response_json = %s,
                        completed_processing_at = NOW(),
                        input_tokens = %s,
                        output_tokens = %s,
                        response_time_ms = %s,
                        overall_score = %s
                    WHERE id = %s
                """, (
                    status,
                    response_data.get('response_text', ''),
                    json.dumps(response_data) if response_data else None,
                    response_data.get('input_tokens', 0),
                    response_data.get('output_tokens', 0),
                    response_data.get('response_time_ms', 0),
                    response_data.get('overall_score'),
                    doc_id
                ))
            else:
                # Failed or timeout status
                kb_cursor.execute("""
                    UPDATE llm_responses 
                    SET status = %s,
                        error_message = %s,
                        completed_processing_at = NOW()
                    WHERE id = %s
                """, (
                    status,
                    response_data.get('error', 'Unknown error') if response_data else 'Processing failed',
                    doc_id
                ))
            
            kb_conn.commit()
            kb_cursor.close()
            kb_conn.close()
            
            # Update batch processed count and check completion for both completed and failed documents
            if status in ['COMPLETED', 'FAILED', 'TIMEOUT']:
                batch = session.query(Batch).filter_by(id=batch_id).first()
                if batch and status == 'COMPLETED':
                    batch.processed_documents = (batch.processed_documents or 0) + 1
                    session.commit()
                    
                # Check if batch is complete (for any final status)
                self.check_and_update_batch_completion(batch_id)
            
            logger.info(f"Updated document {doc_id} status to {status}")
            return True
            
        except Exception as e:
            logger.error(f"Error updating document status: {e}")
            session.rollback()
            return False
        finally:
            session.close()

    def check_and_update_batch_completion(self, batch_id: int) -> bool:
        """
        Check if all documents processed and update batch status
        
        Args:
            batch_id: ID of the batch to check
            
        Returns:
            bool: True if batch is complete, False otherwise
        """
        session = Session()
        try:
            batch = session.query(Batch).filter_by(id=batch_id).first()
            if not batch:
                logger.error(f"Batch {batch_id} not found")
                return False
            
            # Check document processing status in KnowledgeDocuments
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Get counts of different statuses
            kb_cursor.execute("""
                SELECT 
                    COUNT(*) as total,
                    SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as completed,
                    SUM(CASE WHEN status = 'FAILED' THEN 1 ELSE 0 END) as failed,
                    SUM(CASE WHEN status IN ('QUEUED', 'PROCESSING') THEN 1 ELSE 0 END) as pending
                FROM llm_responses
                WHERE batch_id = %s
            """, (batch_id,))
            
            counts = kb_cursor.fetchone()
            kb_cursor.close()
            kb_conn.close()
            
            if not counts:
                logger.warning(f"No responses found for batch {batch_id}")
                return False
                
            total, completed, failed, pending = counts
            
            # Update batch with current counts
            batch.total_documents = total
            batch.processed_documents = completed + failed
            
            # Check if all documents are processed
            if pending == 0:
                # All documents processed
                batch.status = 'COMPLETED'
                batch.completed_at = func.now()
                session.commit()
                
                logger.info(f"Batch {batch_id} completed. Total: {total}, Completed: {completed}, Failed: {failed}")
                return True
            else:
                # Still processing
                session.commit()
                logger.info(f"Batch {batch_id} still processing. Pending: {pending}/{total}")
                return False
                
        except Exception as e:
            logger.error(f"Error checking batch completion: {e}")
            session.rollback()
            return False
        finally:
            session.close()

# Global instance
batch_service = BatchService()
