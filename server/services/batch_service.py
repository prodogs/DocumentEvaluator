"""
Batch Service

Manages batch operations for document processing including:
- Creating new batches with timestamps
- Updating batch status and progress
- Retrieving batch information
- Managing batch lifecycle with timing data
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.sql import func
from sqlalchemy import and_, or_
from models import Batch, Document, LlmResponse, Folder, LlmConfiguration, Prompt, Doc
from database import Session
from services.document_encoding_service import DocumentEncodingService
import os

logger = logging.getLogger(__name__)

class BatchService:
    """Service for managing document processing batches with timestamp tracking"""

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

                    # Scan folder for documents at batch creation time
                    if folder.folder_path and os.path.exists(folder.folder_path):
                        for root, dirs, files in os.walk(folder.folder_path):
                            for filename in files:
                                if filename.lower().endswith(('.pdf', '.txt', '.doc', '.docx')):
                                    filepath = os.path.join(root, filename)
                                    documents_data.append({
                                        'filepath': filepath,
                                        'filename': filename,
                                        'folder_id': folder.id,
                                        'relative_path': os.path.relpath(filepath, folder.folder_path),
                                        'file_size': os.path.getsize(filepath) if os.path.exists(filepath) else 0,
                                        'discovered_at': datetime.now().isoformat()
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

            # STAGE 1: Scan folders and collect all files
            all_file_paths = []
            folder_stats = {}

            folders = session.query(Folder).filter(Folder.id.in_(folder_ids)).all()
            for folder in folders:
                if not folder.folder_path or not os.path.exists(folder.folder_path):
                    logger.warning(f"⚠️ Folder path not found: {folder.folder_path}")
                    continue

                folder_files = []
                for root, _, files in os.walk(folder.folder_path):
                    for filename in files:
                        if filename.lower().endswith(('.pdf', '.txt', '.doc', '.docx', '.rtf', '.odt')):
                            filepath = os.path.join(root, filename)
                            folder_files.append(filepath)
                            all_file_paths.append(filepath)

                folder_stats[folder.id] = {
                    'folder_name': folder.folder_name,
                    'folder_path': folder.folder_path,
                    'file_count': len(folder_files)
                }
                logger.info(f"📁 Found {len(folder_files)} documents in {folder.folder_name}")

            logger.info(f"📄 Total documents to process: {len(all_file_paths)}")

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
                existing_documents = session.query(Document).filter(
                    Document.folder_id == folder_id,
                    Document.batch_id.is_(None)  # Only get documents not already assigned to a batch
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

                    # Create LLM response records for all prompt/connection combinations
                    prompts = config_snapshot['prompts']
                    connections = config_snapshot['connections']

                    for prompt in prompts:
                        for connection in connections:
                            llm_response = LlmResponse(
                                document_id=document.id,
                                prompt_id=prompt['id'],
                                connection_id=connection['id'],
                                status='N',  # Not started
                                task_id=None
                            )
                            session.add(llm_response)
                            responses_created += 1

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
        STAGE 2: Start execution of a prepared batch
        - Changes status from PREPARED to PROCESSING
        - Sets started_at timestamp
        - Initiates LLM processing for all prepared responses

        Args:
            batch_id (int): ID of the batch to run

        Returns:
            Dict[str, Any]: Execution results and status
        """
        session = Session()
        encoding_service = DocumentEncodingService()

        try:
            # Get the batch
            batch = session.query(Batch).filter(Batch.id == batch_id).first()
            if not batch:
                return {'success': False, 'error': f'Batch {batch_id} not found'}

            # Allow running from PREPARED (legacy) or STAGED (new staging workflow)
            if batch.status not in ['PREPARED', 'STAGED']:
                return {'success': False, 'error': f'Batch {batch_id} is not in PREPARED or STAGED status (current: {batch.status})'}

            logger.info(f"🚀 STAGE 2: Starting execution of batch #{batch.batch_number}")

            # Update batch status to ANALYZING (new) or PROCESSING (legacy)
            batch.status = 'ANALYZING' if batch.status == 'STAGED' else 'PROCESSING'
            batch.started_at = func.now()

            # Get all documents in this batch
            documents = session.query(Document).filter(Document.batch_id == batch_id).all()

            # Get all LLM responses that need processing
            responses_to_process = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch_id,
                LlmResponse.status == 'N'  # Not started
            ).all()

            logger.info(f"📄 Found {len(documents)} documents with {len(responses_to_process)} responses to process")

            # Start processing responses (similar to existing process_folder logic)
            from api.document_routes import analyze_document_with_llm
            import asyncio
            import threading

            processed_count = 0
            failed_count = 0

            for response in responses_to_process:
                try:
                    # Get the document
                    document = session.query(Document).filter(Document.id == response.document_id).first()
                    if not document:
                        logger.error(f"❌ Document {response.document_id} not found for response {response.id}")
                        continue

                    # Prepare document data for LLM using encoded content
                    llm_document_data = encoding_service.prepare_document_for_llm(document, session)
                    if not llm_document_data:
                        logger.error(f"❌ Failed to prepare document {document.id} for LLM")
                        response.status = 'F'
                        response.error_message = 'Failed to prepare document data'
                        failed_count += 1
                        continue

                    # Get prompt and connection
                    prompt = session.query(Prompt).filter(Prompt.id == response.prompt_id).first()

                    # Get connection with provider info
                    from sqlalchemy import text
                    connection_result = session.execute(text("""
                        SELECT c.*, p.provider_type, m.display_name as model_name
                        FROM connections c
                        LEFT JOIN llm_providers p ON c.provider_id = p.id
                        LEFT JOIN models m ON c.model_id = m.id
                        WHERE c.id = :connection_id
                    """), {"connection_id": response.connection_id})

                    connection_row = connection_result.fetchone()

                    if not prompt or not connection_row:
                        logger.error(f"❌ Missing prompt or connection for response {response.id}")
                        response.status = 'F'
                        response.error_message = 'Missing prompt or connection'
                        failed_count += 1
                        continue

                    # Prepare metadata for LLM (merge batch and document metadata)
                    combined_meta_data = batch.meta_data.copy() if batch.meta_data else {}
                    if 'document_meta' not in combined_meta_data:
                        combined_meta_data['document_meta'] = {}
                    combined_meta_data['document_meta'].update(document.meta_data)

                    # Update response status to processing
                    response.status = 'P'
                    response.started_processing_at = func.now()
                    session.commit()

                    # Call LLM service (this will be async in real implementation)
                    logger.info(f"🔄 Processing document {document.filename} with {connection_row.name}")

                    # For now, just mark as ready for processing
                    # The actual LLM processing will be handled by the existing background service
                    response.status = 'R'  # Ready for processing
                    processed_count += 1

                except Exception as e:
                    logger.error(f"❌ Error processing response {response.id}: {e}")
                    response.status = 'F'
                    response.error_message = str(e)
                    failed_count += 1

            session.commit()

            logger.info(f"✅ STAGE 2 COMPLETE: Batch #{batch.batch_number} execution started")
            logger.info(f"   🔄 Responses queued for processing: {processed_count}")
            logger.info(f"   ❌ Failed responses: {failed_count}")

            return {
                'success': True,
                'batch_id': batch_id,
                'batch_number': batch.batch_number,
                'batch_name': batch.batch_name,
                'status': batch.status,
                'execution_results': {
                    'total_documents': len(documents),
                    'total_responses': len(responses_to_process),
                    'queued_for_processing': processed_count,
                    'failed_to_queue': failed_count
                }
            }

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error in STAGE 2 batch execution: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

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
        Get overall batch processing statistics

        Args:
            batch_ids (List[int], optional): Filter statistics to specific batch IDs

        Returns:
            Dict[str, Any]: Summary statistics across all batches or filtered batches
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

            # Get overall document and response counts
            total_batches = session.query(Batch).filter(batch_filter).count()
            total_documents = session.query(Document).filter(document_filter).count()

            # Get response counts with batch filtering
            if batch_ids:
                total_responses = session.query(LlmResponse).join(Document).filter(
                    Document.batch_id.in_(batch_ids)
                ).count()

                response_counts = session.query(
                    LlmResponse.status,
                    func.count(LlmResponse.id).label('count')
                ).join(Document).filter(
                    Document.batch_id.in_(batch_ids)
                ).group_by(LlmResponse.status).all()

                # Calculate average processing time for filtered batches
                avg_processing_time = session.query(
                    func.avg(LlmResponse.response_time_ms)
                ).join(Document).filter(
                    Document.batch_id.in_(batch_ids),
                    LlmResponse.status == 'S',
                    LlmResponse.response_time_ms.isnot(None)
                ).scalar()
            else:
                total_responses = session.query(LlmResponse).count()

                response_counts = session.query(
                    LlmResponse.status,
                    func.count(LlmResponse.id).label('count')
                ).group_by(LlmResponse.status).all()

                # Calculate average processing time
                avg_processing_time = session.query(
                    func.avg(LlmResponse.response_time_ms)
                ).filter(
                    LlmResponse.status == 'S',
                    LlmResponse.response_time_ms.isnot(None)
                ).scalar()

            response_status_counts = {status: count for status, count in response_counts}

            # Get recent activity (last 24 hours)
            from datetime import timedelta
            day_ago = datetime.utcnow() - timedelta(days=1)
            recent_batches = session.query(Batch).filter(
                and_(Batch.created_at >= day_ago, batch_filter)
            ).count()

            recent_documents = session.query(Document).filter(
                and_(Document.created_at >= day_ago, document_filter)
            ).count()

            # Calculate document-level success rate for summary stats
            # Get all documents in the filtered batches and check their completion status
            successful_documents = 0
            total_processed_documents = 0

            if batch_ids:
                # For filtered batches, calculate document-level completion
                filtered_documents = session.query(Document).filter(Document.batch_id.in_(batch_ids)).all()
                for doc in filtered_documents:
                    doc_responses = session.query(LlmResponse).filter(LlmResponse.document_id == doc.id).all()
                    if doc_responses and all(r.status in ['S', 'F'] for r in doc_responses):
                        total_processed_documents += 1
                        # Check if document has any successful responses
                        if any(r.status == 'S' for r in doc_responses):
                            successful_documents += 1
            else:
                # For all batches, calculate document-level completion
                all_documents = session.query(Document).all()
                for doc in all_documents:
                    doc_responses = session.query(LlmResponse).filter(LlmResponse.document_id == doc.id).all()
                    if doc_responses and all(r.status in ['S', 'F'] for r in doc_responses):
                        total_processed_documents += 1
                        # Check if document has any successful responses
                        if any(r.status == 'S' for r in doc_responses):
                            successful_documents += 1

            return {
                'total_batches': total_batches,
                'batch_status_counts': status_counts,
                'total_documents': total_documents,
                'total_responses': total_responses,
                'response_status_counts': response_status_counts,
                'avg_processing_time_ms': round(avg_processing_time, 2) if avg_processing_time else 0,
                'recent_activity': {
                    'batches_24h': recent_batches,
                    'documents_24h': recent_documents
                },
                'success_rate': round(successful_documents / total_processed_documents * 100, 1) if total_processed_documents > 0 else 0,
                'active_batches': status_counts.get('P', 0),
                'filtered_batch_ids': batch_ids
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

            if batch.status != 'P':
                return {'success': False, 'error': f'Batch {batch_id} is not currently processing (status: {batch.status})'}

            batch.status = 'PA'  # Paused
            session.commit()

            logger.info(f"Paused batch {batch_id} (#{batch.batch_number} - '{batch.batch_name}')")
            return {
                'success': True,
                'message': f'Batch {batch.batch_number} paused successfully',
                'batch_id': batch_id,
                'status': 'PA'
            }

        except Exception as e:
            logger.error(f"Error pausing batch {batch_id}: {e}", exc_info=True)
            session.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def resume_batch(self, batch_id: int) -> Dict[str, Any]:
        """
        Resume a paused batch - allows new documents to be submitted for processing

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

            if batch.status != 'PA':
                return {'success': False, 'error': f'Batch {batch_id} is not paused (status: {batch.status})'}

            batch.status = 'P'  # Processing
            session.commit()

            logger.info(f"Resumed batch {batch_id} (#{batch.batch_number} - '{batch.batch_name}')")
            return {
                'success': True,
                'message': f'Batch {batch.batch_number} resumed successfully',
                'batch_id': batch_id,
                'status': 'P'
            }

        except Exception as e:
            logger.error(f"Error resuming batch {batch_id}: {e}", exc_info=True)
            session.rollback()
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

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

            # Count completed LLM responses for documents in this batch
            completed_responses = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch_id,
                LlmResponse.status.in_(['S', 'F'])  # Success or Failure
            ).count()

            # Count total expected responses for documents in this batch
            total_responses = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch_id
            ).count()

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
                    # No responses means no documents to process - mark as completed
                    batch.status = 'COMPLETED'  # Use new COMPLETED status
                    batch.completed_at = func.now()

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

            # Get response statistics
            response_stats = session.query(
                LlmResponse.status,
                func.count(LlmResponse.id).label('count')
            ).join(Document).filter(
                Document.batch_id == batch_id
            ).group_by(LlmResponse.status).all()

            status_counts = {status: count for status, count in response_stats}
            total_responses = sum(status_counts.values())

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
                'completion_percentage': (status_counts.get('S', 0) + status_counts.get('F', 0)) / total_responses * 100 if total_responses > 0 else 0
            }

        except Exception as e:
            logger.error(f"Error getting batch info {batch_id}: {e}", exc_info=True)
            return None
        finally:
            session.close()

    def list_batches(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List recent batches with summary information

        Args:
            limit (int): Maximum number of batches to return

        Returns:
            list: List of batch summaries
        """
        session = Session()
        try:
            batches = session.query(Batch).order_by(Batch.created_at.desc()).limit(limit).all()

            batch_list = []
            for batch in batches:
                # Get document count for this batch
                document_count = session.query(Document).filter_by(batch_id=batch.id).count()

                # Get completion status
                completed_responses = session.query(LlmResponse).join(Document).filter(
                    Document.batch_id == batch.id,
                    LlmResponse.status.in_(['S', 'F'])
                ).count()

                total_responses = session.query(LlmResponse).join(Document).filter(
                    Document.batch_id == batch.id
                ).count()

                batch_list.append({
                    'id': batch.id,
                    'batch_number': batch.batch_number,
                    'batch_name': batch.batch_name,
                    'status': batch.status,
                    'created_at': batch.created_at.isoformat() if batch.created_at else None,
                    'total_documents': document_count,
                    'completion_percentage': (completed_responses / total_responses * 100) if total_responses > 0 else 0
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

# Global instance
batch_service = BatchService()
