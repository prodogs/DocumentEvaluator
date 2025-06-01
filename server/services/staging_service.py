"""
Staging Service

Manages the new staging workflow for document processing batches:
- Save Analysis: Creates batch with SAVED status
- Stage Analysis: Creates batch and starts preprocessing (STAGING -> STAGED)
- Manages the new batch lifecycle
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.sql import func
from sqlalchemy import text
from models import Batch, Document, LlmResponse, Folder, Prompt, Doc, Connection
from database import Session
from services.document_encoding_service import DocumentEncodingService
from services.config import config_manager
import os

logger = logging.getLogger(__name__)

class StagingService:
    """Service for managing the new staging workflow"""

    def save_analysis(self, folder_ids: List[int], connection_ids: List[int], prompt_ids: List[int],
                     batch_name: Optional[str] = None, description: Optional[str] = None,
                     meta_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Save Analysis: Create a batch with SAVED status
        
        Args:
            folder_ids (List[int]): List of folder IDs to include in this batch
            batch_name (str, optional): User-friendly name for the batch
            description (str, optional): Description of the batch
            meta_data (Dict[str, Any], optional): JSON metadata to be sent to LLM for context
            
        Returns:
            Dict[str, Any]: The created batch data
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

            # Create configuration snapshot with selected configs and prompts
            config_snapshot = self._create_config_snapshot(folder_ids, connection_ids, prompt_ids)

            # Create the batch with SAVED status
            batch = Batch(
                batch_number=next_batch_number,
                batch_name=batch_name,
                description=description,
                folder_ids=folder_ids,
                folder_path=None,  # Legacy field, not used for multi-folder batches
                meta_data=meta_data,
                config_snapshot=config_snapshot,
                status='SAVED',  # New: Saved but not staged
                started_at=None,  # Will be set when staging starts
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
                'folder_ids': batch.folder_ids,
                'meta_data': batch.meta_data,
                'status': batch.status,
                'created_at': batch.created_at.isoformat() if batch.created_at else None
            }

            logger.info(f"✅ SAVED: Batch #{next_batch_number} - {batch_name} saved successfully")
            return {
                'success': True,
                'message': f'Analysis configuration saved as Batch #{next_batch_number}',
                'batch': batch_data
            }

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error saving analysis: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def stage_analysis(self, folder_ids: List[int], connection_ids: List[int], prompt_ids: List[int],
                      batch_name: Optional[str] = None, description: Optional[str] = None,
                      meta_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Stage Analysis: Create batch and start preprocessing
        
        Args:
            folder_ids (List[int]): List of folder IDs to include in this batch
            batch_name (str, optional): User-friendly name for the batch
            description (str, optional): Description of the batch
            meta_data (Dict[str, Any], optional): JSON metadata to be sent to LLM for context
            
        Returns:
            Dict[str, Any]: The created batch data and staging results
        """
        session = Session()
        encoding_service = DocumentEncodingService()
        
        try:
            # Get the next batch number
            max_batch_number = session.query(func.max(Batch.batch_number)).scalar()
            next_batch_number = (max_batch_number or 0) + 1

            # Generate default batch name if not provided
            if not batch_name:
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                batch_name = f"Batch #{next_batch_number} - {timestamp}"

            # Create configuration snapshot with selected configs and prompts
            config_snapshot = self._create_config_snapshot(folder_ids, connection_ids, prompt_ids)

            # Create the batch with STAGING status
            batch = Batch(
                batch_number=next_batch_number,
                batch_name=batch_name,
                description=description,
                folder_ids=folder_ids,
                folder_path=None,  # Legacy field, not used for multi-folder batches
                meta_data=meta_data,
                config_snapshot=config_snapshot,
                status='STAGING',  # New: Staging in progress
                started_at=func.now(),  # Mark when staging started
                total_documents=0,
                processed_documents=0
            )

            session.add(batch)
            session.commit()
            batch_id = batch.id

            logger.info(f"🎯 STAGING: Starting preprocessing for Batch #{next_batch_number}")

            # Start preprocessing in background
            try:
                staging_results = self._perform_staging(session, batch_id, folder_ids, connection_ids, prompt_ids, encoding_service)
                
                # Update batch status based on staging results
                if staging_results['success']:
                    batch.status = 'STAGED'
                    batch.total_documents = staging_results['total_documents']
                    logger.info(f"✅ STAGED: Batch #{next_batch_number} staging completed successfully")
                else:
                    batch.status = 'FAILED_STAGING'
                    logger.error(f"❌ FAILED_STAGING: Batch #{next_batch_number} staging failed")
                
                session.commit()

                # Extract data before closing session
                batch_data = {
                    'id': batch.id,
                    'batch_number': batch.batch_number,
                    'batch_name': batch.batch_name,
                    'description': batch.description,
                    'folder_ids': batch.folder_ids,
                    'meta_data': batch.meta_data,
                    'status': batch.status,
                    'created_at': batch.created_at.isoformat() if batch.created_at else None,
                    'started_at': batch.started_at.isoformat() if batch.started_at else None,
                    'total_documents': batch.total_documents
                }

                return {
                    'success': True,
                    'message': f'Batch #{next_batch_number} staged successfully' if staging_results['success'] 
                              else f'Batch #{next_batch_number} staging failed',
                    'batch': batch_data,
                    'staging_results': staging_results
                }

            except Exception as staging_error:
                # Mark batch as failed staging
                batch.status = 'FAILED_STAGING'
                session.commit()
                logger.error(f"❌ FAILED_STAGING: Error during staging: {staging_error}")
                
                return {
                    'success': False,
                    'error': f'Staging failed: {str(staging_error)}',
                    'batch_id': batch_id
                }

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error staging analysis: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def reprocess_existing_batch_staging(self, batch_id: int, folder_ids: List[int],
                                       batch_name: Optional[str] = None,
                                       meta_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Reprocess staging for an existing batch (updates the existing batch instead of creating new one)

        Args:
            batch_id (int): ID of the existing batch to reprocess
            folder_ids (List[int]): List of folder IDs to include in this batch
            batch_name (str, optional): User-friendly name for the batch
            meta_data (Dict[str, Any], optional): JSON metadata to be sent to LLM for context

        Returns:
            Dict[str, Any]: The updated batch data and staging results
        """
        session = Session()
        encoding_service = DocumentEncodingService()

        try:
            # Get the existing batch
            batch = session.query(Batch).filter(Batch.id == batch_id).first()
            if not batch:
                return {'success': False, 'error': f'Batch {batch_id} not found'}

            if batch.status not in ['SAVED', 'FAILED_STAGING']:
                return {'success': False, 'error': f'Batch {batch_id} is not in a state that allows reprocessing staging (current: {batch.status})'}

            logger.info(f"🎯 REPROCESSING: Starting staging for existing Batch #{batch.batch_number}")

            # Clean up existing LLM responses for this batch to avoid duplicates
            existing_responses = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch_id
            ).all()

            if existing_responses:
                logger.info(f"🧹 CLEANUP: Removing {len(existing_responses)} existing LLM responses")
                for response in existing_responses:
                    session.delete(response)

            # Update batch status to STAGING
            batch.status = 'STAGING'
            batch.started_at = func.now()  # Update start time

            # Extract existing configs and prompts from current config snapshot
            existing_config_snapshot = batch.config_snapshot or {}
            # Support both old and new config snapshot formats
            existing_connection_ids = [config['id'] for config in existing_config_snapshot.get('connections', [])]
            if not existing_connection_ids:
                # Fallback to old format for backward compatibility
                existing_connection_ids = [config['id'] for config in existing_config_snapshot.get('llm_configurations', [])]
            existing_prompt_ids = [prompt['id'] for prompt in existing_config_snapshot.get('prompts', [])]

            # Update configuration snapshot if needed (keep existing selections)
            config_snapshot = self._create_config_snapshot(folder_ids, existing_connection_ids, existing_prompt_ids)
            batch.config_snapshot = config_snapshot

            session.commit()

            # Use the existing configs and prompts from the updated config snapshot
            connection_ids = existing_connection_ids
            prompt_ids = existing_prompt_ids

            # Start preprocessing
            try:
                staging_results = self._perform_staging(session, batch_id, folder_ids, connection_ids, prompt_ids, encoding_service)

                # Update batch status based on staging results
                if staging_results['success']:
                    batch.status = 'STAGED'
                    batch.total_documents = staging_results['total_documents']
                    logger.info(f"✅ STAGED: Batch #{batch.batch_number} reprocessing completed successfully")
                else:
                    batch.status = 'FAILED_STAGING'
                    logger.error(f"❌ FAILED_STAGING: Batch #{batch.batch_number} reprocessing failed")

                session.commit()

                # Extract data before closing session
                batch_data = {
                    'id': batch.id,
                    'batch_number': batch.batch_number,
                    'batch_name': batch.batch_name,
                    'description': batch.description,
                    'folder_ids': batch.folder_ids,
                    'meta_data': batch.meta_data,
                    'status': batch.status,
                    'total_documents': batch.total_documents,
                    'created_at': batch.created_at.isoformat() if batch.created_at else None,
                    'started_at': batch.started_at.isoformat() if batch.started_at else None
                }

                return {
                    'success': staging_results['success'],
                    'message': f'Batch #{batch.batch_number} staging {"completed" if staging_results["success"] else "failed"}',
                    'batch': batch_data,
                    'staging_results': staging_results
                }

            except Exception as staging_error:
                # Mark batch as failed staging
                batch.status = 'FAILED_STAGING'
                session.commit()
                logger.error(f"❌ FAILED_STAGING: Error during reprocessing: {staging_error}")

                return {
                    'success': False,
                    'error': f'Staging failed: {str(staging_error)}',
                    'batch_id': batch_id
                }

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error reprocessing staging for batch {batch_id}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def _perform_staging(self, session: Session, batch_id: int, folder_ids: List[int],
                        connection_ids: List[int], prompt_ids: List[int],
                        encoding_service: DocumentEncodingService) -> Dict[str, Any]:
        """
        Perform the actual staging process: scan folders, create documents, encode, create LLM responses
        
        Args:
            session: Database session
            batch_id: ID of the batch being staged
            folder_ids: List of folder IDs to process
            encoding_service: Service for document encoding
            
        Returns:
            Dict[str, Any]: Staging results
        """
        try:
            total_documents = 0
            total_responses = 0
            failed_documents = 0

            # Get folders
            folders = session.query(Folder).filter(Folder.id.in_(folder_ids)).all()
            if not folders:
                return {'success': False, 'error': 'No valid folders found'}

            # Get selected connections and prompts (not all active ones)
            if connection_ids:
                connections = session.query(Connection).filter(Connection.id.in_(connection_ids)).all()
            else:
                connections = []

            if prompt_ids:
                prompts = session.query(Prompt).filter(Prompt.id.in_(prompt_ids)).all()
            else:
                prompts = []

            if not connections:
                return {'success': False, 'error': 'No selected connections found'}
            if not prompts:
                return {'success': False, 'error': 'No selected prompts found'}

            # Process each folder
            for folder in folders:
                folder_path = folder.folder_path
                if not os.path.exists(folder_path):
                    logger.warning(f"Folder path does not exist: {folder_path}")
                    continue

                # Scan folder for documents
                for root, dirs, files in os.walk(folder_path):
                    for file in files:
                        if file.lower().endswith(('.txt', '.pdf', '.docx', '.doc')):
                            file_path = os.path.join(root, file)

                            # Check file size before processing
                            try:
                                file_size = os.path.getsize(file_path)
                                doc_config = config_manager.get_document_config()

                                if file_size > doc_config.max_file_size_bytes:
                                    logger.warning(f"⚠️ Skipping file (too large): {file} ({file_size} bytes > {doc_config.max_file_size_display})")
                                    continue

                                if file_size < doc_config.min_file_size_bytes:
                                    logger.warning(f"⚠️ Skipping file (too small): {file} ({file_size} bytes)")
                                    continue
                            except OSError as e:
                                logger.warning(f"⚠️ Cannot access file: {file} - {e}")
                                continue

                            try:
                                # Check if document already exists
                                existing_document = session.query(Document).filter(Document.filepath == file_path).first()

                                if existing_document:
                                    # Check if file has changed (compare file modification time or size)
                                    file_stat = os.stat(file_path)
                                    current_file_size = file_stat.st_size
                                    current_mod_time = file_stat.st_mtime

                                    # Check if we need to refresh the document content
                                    needs_refresh = False
                                    if existing_document.doc_id:
                                        existing_doc = session.query(Doc).filter(Doc.id == existing_document.doc_id).first()
                                        if existing_doc:
                                            # Compare file size (simple check for changes)
                                            if existing_doc.file_size != current_file_size:
                                                needs_refresh = True
                                                logger.info(f"📄 File size changed for {file}: {existing_doc.file_size} -> {current_file_size}")
                                        else:
                                            needs_refresh = True  # Doc record missing
                                    else:
                                        needs_refresh = True  # No doc_id linked

                                    if needs_refresh:
                                        # Re-encode the document
                                        doc_record = encoding_service.encode_and_store_document(file_path, session)
                                        if doc_record:
                                            existing_document.doc_id = doc_record.id
                                            logger.info(f"📄 Refreshed document content: {file}")
                                        else:
                                            logger.warning(f"⚠️ Failed to refresh document content: {file}")

                                    # Use existing document
                                    document = existing_document
                                    logger.info(f"📄 Using existing document: {file}")
                                else:
                                    # Create new document record
                                    document = Document(
                                        filepath=file_path,
                                        filename=file,
                                        folder_id=folder.id,
                                        batch_id=batch_id,
                                        meta_data={'source_folder': folder_path},
                                        valid='Y'
                                    )
                                    session.add(document)
                                    session.flush()  # Get the document ID
                                    logger.info(f"📄 Created new document: {file}")
                                
                                # Encode document (if it's a new document OR if existing document lacks doc_id)
                                if not existing_document or not existing_document.doc_id:
                                    doc_id = encoding_service.encode_and_store_document(file_path, session)
                                    if doc_id:
                                        document.doc_id = doc_id
                                        total_documents += 1
                                        if existing_document:
                                            logger.info(f"📄 Encoded existing document (missing doc_id): {file}")
                                        else:
                                            logger.info(f"📄 Encoded new document: {file}")
                                    else:
                                        logger.warning(f"⚠️ Failed to encode document: {file}")
                                else:
                                    logger.info(f"📄 Document already encoded (doc_id: {existing_document.doc_id}): {file}")

                                # Update batch_id for the document (whether new or existing)
                                document.batch_id = batch_id

                                # Check if LLM responses already exist for this document in this batch
                                existing_responses_for_doc = session.query(LlmResponse).filter(
                                    LlmResponse.document_id == document.id
                                ).join(Document).filter(
                                    Document.batch_id == batch_id
                                ).all()

                                if not existing_responses_for_doc:
                                    # Create LLM response records for each combination only if none exist for this batch
                                    for connection in connections:
                                        for prompt in prompts:
                                            llm_response = LlmResponse(
                                                document_id=document.id,
                                                connection_id=connection.id,
                                                prompt_id=prompt.id,
                                                status='N'  # Not started
                                            )
                                            session.add(llm_response)
                                            total_responses += 1
                                    logger.info(f"📄 Created {len(connections) * len(prompts)} LLM responses for document: {file}")
                                else:
                                    # Responses already exist for this batch, just count them
                                    total_responses += len(existing_responses_for_doc)
                                    logger.info(f"📄 Using {len(existing_responses_for_doc)} existing LLM responses for document: {file}")
                                    
                            except Exception as doc_error:
                                failed_documents += 1
                                logger.error(f"Error processing document {file_path}: {doc_error}")

            session.commit()
            
            logger.info(f"📊 Staging completed: {total_documents} documents, {total_responses} responses, {failed_documents} failed")
            
            return {
                'success': True,
                'total_documents': total_documents,
                'total_responses': total_responses,
                'failed_documents': failed_documents
            }

        except Exception as e:
            logger.error(f"❌ Error in staging process: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}

    def _create_config_snapshot(self, folder_ids: List[int], connection_ids: List[int], prompt_ids: List[int]) -> Dict[str, Any]:
        """Create a snapshot of the current configuration with selected configs and prompts"""
        session = Session()
        try:
            # Get folder information
            folders = session.query(Folder).filter(Folder.id.in_(folder_ids)).all()
            folder_data = [
                {
                    'id': folder.id,
                    'folder_path': folder.folder_path,
                    'folder_name': folder.folder_name,
                    'active': folder.active
                }
                for folder in folders
            ]

            # Get selected connections
            if connection_ids:
                connections = session.query(Connection).filter(Connection.id.in_(connection_ids)).all()
                connection_data = [
                    {
                        'id': connection.id,
                        'name': connection.name,
                        'base_url': connection.base_url,
                        'provider_id': connection.provider_id,
                        'model_id': connection.model_id
                    }
                    for connection in connections
                ]
            else:
                connection_data = []

            # Get selected prompts
            if prompt_ids:
                prompts = session.query(Prompt).filter(Prompt.id.in_(prompt_ids)).all()
                prompt_data = [
                    {
                        'id': prompt.id,
                        'description': prompt.description,
                        'prompt_text': prompt.prompt_text[:100] + '...' if len(prompt.prompt_text) > 100 else prompt.prompt_text
                    }
                    for prompt in prompts
                ]
            else:
                prompt_data = []

            return {
                'folders': folder_data,
                'connections': connection_data,
                'prompts': prompt_data,
                'snapshot_created_at': datetime.now().isoformat()
            }

        except Exception as e:
            logger.error(f"Error creating config snapshot: {e}")
            return {'error': str(e)}
        finally:
            session.close()

# Create a singleton instance
staging_service = StagingService()
