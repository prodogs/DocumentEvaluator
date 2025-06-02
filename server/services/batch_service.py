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
from models import Batch, Document, Folder, Connection, Prompt
from database import Session
from services.document_encoding_service import DocumentEncodingService
import os

logger = logging.getLogger(__name__)

class BatchService:
    """Service for managing document processing batches - LLM processing moved to KnowledgeDocuments database"""

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
            if batch.status in ['READY', 'STAGED']:
                # Batch has been staged but needs LLM responses created
                return self._run_ready_batch(session, batch)
            elif batch.status == 'PREPARED':
                # Batch has LLM responses ready, start processing
                return self._deprecated_run_batch(batch_id)
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
            # HOTFIX: Get fresh connection data from DB to avoid corrupted snapshot data
            from sqlalchemy import text
            fresh_connections_result = session.execute(text("""
                SELECT c.*, p.provider_type, m.display_name as model_name
                FROM connections c
                LEFT JOIN llm_providers p ON c.provider_id = p.id
                LEFT JOIN models m ON c.model_id = m.id
                WHERE c.is_active = true
            """))
            
            fresh_connections_data = []
            for row in fresh_connections_result:
                fresh_connections_data.append({
                    'id': row.id,
                    'name': row.name,
                    'base_url': row.base_url,
                    'model_name': row.model_name or 'default',
                    'api_key': row.api_key,
                    'provider_type': row.provider_type,
                    'port_no': row.port_no,
                    'is_active': row.is_active
                })
            
            connections = fresh_connections_data  # Use fresh data instead of snapshot
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
                            # Prepare LLM provider data from connection
                            llm_provider_data = {
                                'provider_type': connection.get('provider_type', 'ollama'),
                                'url': connection.get('base_url', 'http://localhost'),
                                'model_name': connection.get('model_name', 'default'),
                                'api_key': connection.get('api_key'),
                                'port_no': connection.get('port_no', 11434)
                            }

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
                                    
                                    # Validate the encoded content
                                    if len(encoded_content) == 1398101:
                                        logger.warning(f"⚠️ Document has exactly 1398101 characters - checking for corruption")
                                        # Try to decode it back to verify it's valid
                                        try:
                                            test_decode = base64.b64decode(encoded_content)
                                            logger.info(f"✅ Base64 validation passed")
                                        except Exception as decode_error:
                                            logger.error(f"❌ Base64 validation failed: {decode_error}")
                                            # Try to fix padding
                                            missing_padding = len(encoded_content) % 4
                                            if missing_padding:
                                                encoded_content += '=' * (4 - missing_padding)
                                                logger.info(f"🔧 Added {4 - missing_padding} padding characters")
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
                                        
                                        cursor.execute("""
                                            INSERT INTO docs (content, content_type, doc_type, file_size, encoding, created_at, document_id)
                                            VALUES (%s, %s, %s, %s, %s, NOW(), %s)
                                            RETURNING id
                                        """, (
                                            encoded_content,
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
                                # IMPORTANT: Use exact configuration from database - NEVER modify values
                                base_url = connection.get('base_url', '')
                                port_no = connection.get('port_no')
                                
                                logger.info(f"🔍 Connection data: {connection}")
                                logger.info(f"🔍 LLM provider data: {llm_provider_data}")
                                logger.info(f"🔍 Base URL from DB (exact): '{base_url}'")
                                logger.info(f"🔍 Port from DB (exact): {port_no}")

                                # Ensure base_url is not empty
                                if not base_url:
                                    logger.error(f"❌ Empty base_url for connection {connection.get('id')}")
                                    failed_count += 1
                                    continue

                                # Use exact database values without modification
                                logger.info(f"🔗 Using exact LLM provider configuration from database")

                                # Prepare LLM provider config for RAG service using exact DB values
                                llm_config = {
                                    'provider_type': llm_provider_data.get('provider_type'),
                                    'base_url': base_url,  # Use exact base_url from database
                                    'port_no': port_no,    # Use exact port_no from database
                                    'model_name': llm_provider_data.get('model_name'),
                                    'api_key': llm_provider_data.get('api_key')
                                }

                                logger.info(f"🔧 LLM Config being sent: {llm_config}")

                                form_data = {
                                    'doc_id': str(doc_id),
                                    'prompts': json.dumps(prompts_data),
                                    'llm_provider': json.dumps(llm_config),
                                    'meta_data': json.dumps(meta_data)
                                }

                                # Send to RAG API
                                import requests
                                response_raw = requests.post(
                                    "http://localhost:7001/analyze_document_with_llm",
                                    data=form_data,
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

    def _deprecated_run_batch(self, batch_id: int) -> Dict[str, Any]:
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

    def restage_and_rerun_batch(self, batch_id: int) -> Dict[str, Any]:
        """
        Restage and rerun analysis for a completed batch
        - Validates batch is in COMPLETED status
        - Deletes all existing LLM responses
        - Refreshes documents and docs (checks for file changes)
        - Recreates LLM responses for all connection/prompt combinations
        - Updates batch status and timing
        - Initiates LLM processing for all new responses

        Args:
            batch_id (int): ID of the batch to restage and rerun

        Returns:
            Dict[str, Any]: Execution results and status
        """
        session = Session()

        try:
            # Get the batch
            batch = session.query(Batch).filter(Batch.id == batch_id).first()
            if not batch:
                return {'success': False, 'error': f'Batch {batch_id} not found'}

            # Only allow restaging completed batches
            if batch.status != 'COMPLETED':
                return {'success': False, 'error': f'Batch {batch_id} is not completed (current: {batch.status}). Only completed batches can be restaged.'}

            logger.info(f"🔄 RESTAGE: Starting restage and rerun of completed batch #{batch.batch_number}")

            # Step 1: Delete all existing LLM responses for this batch
            responses_to_delete = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch_id
            ).all()

            deleted_responses_count = len(responses_to_delete)
            for response in responses_to_delete:
                session.delete(response)

            logger.info(f"🗑️ RESTAGE: Deleted {deleted_responses_count} existing LLM responses")

            # Step 2: Get batch configuration for restaging
            config_snapshot = batch.config_snapshot or {}
            connection_ids = [config['id'] for config in config_snapshot.get('connections', [])]
            if not connection_ids:
                # Fallback to old format for backward compatibility
                connection_ids = [config['id'] for config in config_snapshot.get('llm_configurations', [])]
            prompt_ids = [prompt['id'] for prompt in config_snapshot.get('prompts', [])]
            folder_ids = batch.folder_ids or []

            if not connection_ids or not prompt_ids:
                return {'success': False, 'error': 'Batch configuration is incomplete - missing connections or prompts'}

            # Step 3: Refresh documents and docs (check for file changes)
            from services.staging_service import StagingService
            from services.document_encoding_service import DocumentEncodingService

            staging_service = StagingService()
            encoding_service = DocumentEncodingService()

            # Update batch status to STAGING for restaging
            batch.status = 'STAGING'
            batch.started_at = func.now()
            batch.completed_at = None
            batch.processed_documents = 0

            session.commit()

            logger.info(f"🔄 RESTAGE: Starting document refresh and restaging for batch #{batch.batch_number}")

            # Step 4: Perform restaging (this will refresh documents and create new LLM responses)
            staging_results = staging_service._perform_staging(
                session, batch_id, folder_ids, connection_ids, prompt_ids, encoding_service
            )

            if not staging_results['success']:
                batch.status = 'FAILED_STAGING'
                session.commit()
                return {
                    'success': False,
                    'error': f'Restaging failed: {staging_results.get("error", "Unknown error")}',
                    'batch_id': batch_id
                }

            # Step 5: Update batch status to STAGED and then start processing
            batch.status = 'STAGED'
            batch.total_documents = staging_results['total_documents']
            session.commit()

            logger.info(f"✅ RESTAGE: Batch #{batch.batch_number} restaging completed successfully")

            # Step 6: Start LLM processing for all new responses
            batch.status = 'ANALYZING'
            session.commit()

            # Get all new LLM responses that need processing
            responses_to_process = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch_id,
                LlmResponse.status == 'N'  # Not started
            ).all()

            processed_count = 0
            failed_count = 0

            # The responses are already created with status 'N' (Not started)
            # The dynamic processing queue will automatically pick them up
            # No need to manually queue them - just count them
            for response in responses_to_process:
                if response.status == 'N':
                    processed_count += 1
                else:
                    failed_count += 1

            session.commit()

            logger.info(f"✅ RESTAGE COMPLETE: Batch #{batch.batch_number} restage and rerun started")
            logger.info(f"   🔄 Documents refreshed: {staging_results['total_documents']}")
            logger.info(f"   🗑️ Old responses deleted: {deleted_responses_count}")
            logger.info(f"   ➕ New responses created: {len(responses_to_process)}")
            logger.info(f"   🔄 Responses queued for processing: {processed_count}")
            logger.info(f"   ❌ Failed to queue: {failed_count}")

            return {
                'success': True,
                'batch_id': batch_id,
                'batch_number': batch.batch_number,
                'batch_name': batch.batch_name,
                'status': batch.status,
                'restage_results': {
                    'total_documents': staging_results['total_documents'],
                    'deleted_responses': deleted_responses_count,
                    'new_responses_created': len(responses_to_process),
                    'queued_for_processing': processed_count,
                    'failed_to_queue': failed_count,
                    'staging_details': staging_results
                }
            }

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error in restage and rerun for batch {batch_id}: {e}", exc_info=True)
            return {'success': False, 'error': str(e)}
        finally:
            session.close()

    def rerun_batch(self, batch_id: int) -> Dict[str, Any]:
        """DEPRECATED: Batch rerun moved to KnowledgeDocuments database"""
        return self._handle_llm_response_deprecation('rerun_batch')

    def _deprecated_rerun_batch(self, batch_id: int) -> Dict[str, Any]:
        """
        Rerun analysis for a completed batch
        - Validates batch is in COMPLETED status
        - Resets all LLM responses to 'N' (Not started)
        - Clears response data and timing fields
        - Updates batch status and timing
        - Initiates LLM processing for all reset responses

        Args:
            batch_id (int): ID of the batch to rerun

        Returns:
            Dict[str, Any]: Execution results and status
        """
        session = Session()

        try:
            # Get the batch
            batch = session.query(Batch).filter(Batch.id == batch_id).first()
            if not batch:
                return {'success': False, 'error': f'Batch {batch_id} not found'}

            # Only allow rerunning completed batches
            if batch.status != 'COMPLETED':
                return {'success': False, 'error': f'Batch {batch_id} is not completed (current: {batch.status}). Only completed batches can be rerun.'}

            logger.info(f"🔄 RERUN: Starting rerun of completed batch #{batch.batch_number}")

            # Reset all LLM responses for this batch
            responses_to_reset = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch_id
            ).all()

            reset_count = 0
            for response in responses_to_reset:
                # Reset response to initial state
                response.status = 'N'  # Not started
                response.started_processing_at = None
                response.completed_processing_at = None
                response.response_json = None
                response.response_text = None
                response.response_time_ms = None
                response.error_message = None
                response.overall_score = None
                response.input_tokens = None
                response.output_tokens = None
                response.task_id = None
                reset_count += 1

            # Reset batch status and timing
            batch.status = 'ANALYZING'
            batch.started_at = func.now()
            batch.completed_at = None
            batch.processed_documents = 0

            session.commit()

            logger.info(f"✅ RERUN RESET: Reset {reset_count} LLM responses for batch #{batch.batch_number}")

            # Now run the batch using existing logic
            # Get all documents in this batch
            documents = session.query(Document).filter(Document.batch_id == batch_id).all()

            # Get all LLM responses that need processing (should be all of them now)
            responses_to_process = session.query(LlmResponse).join(Document).filter(
                Document.batch_id == batch_id,
                LlmResponse.status == 'N'  # Not started
            ).all()

            logger.info(f"🚀 RERUN PROCESSING: Starting processing of {len(responses_to_process)} responses")

            processed_count = 0
            failed_count = 0

            for response in responses_to_process:
                try:
                    # Get document
                    document = session.query(Document).filter(Document.id == response.document_id).first()
                    if not document:
                        logger.error(f"❌ Document not found for response {response.id}")
                        response.status = 'F'
                        response.error_message = 'Document not found'
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
                    logger.info(f"🔄 Reprocessing document {document.filename} with {connection_row.name}")

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

            logger.info(f"✅ RERUN COMPLETE: Batch #{batch.batch_number} rerun started")
            logger.info(f"   🔄 Responses queued for processing: {processed_count}")
            logger.info(f"   ❌ Failed responses: {failed_count}")

            return {
                'success': True,
                'batch_id': batch_id,
                'batch_number': batch.batch_number,
                'batch_name': batch.batch_name,
                'status': batch.status,
                'rerun_results': {
                    'total_documents': len(documents),
                    'total_responses_reset': reset_count,
                    'total_responses': len(responses_to_process),
                    'queued_for_processing': processed_count,
                    'failed_to_queue': failed_count
                }
            }

        except Exception as e:
            session.rollback()
            logger.error(f"❌ Error in batch rerun: {e}", exc_info=True)
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

            if batch.status not in ['P', 'ANALYZING']:
                return {'success': False, 'error': f'Batch {batch_id} is not currently processing (status: {batch.status}). Can only pause ANALYZING or PROCESSING batches.'}

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

            # Allow resuming PAUSED or ANALYZING batches (ANALYZING might be stuck)
            if batch.status not in ['PAUSED', 'ANALYZING']:
                return {'success': False, 'error': f'Batch {batch_id} cannot be resumed (status: {batch.status}). Can only resume PAUSED or ANALYZING batches.'}

            logger.info(f"🔄 Resuming batch {batch_id} (#{batch.batch_number} - '{batch.batch_name}') from status {batch.status}")

            # Update batch status to analyzing
            batch.status = 'ANALYZING'
            batch.started_at = func.now()  # Update start time
            session.commit()

            # Now actually process the documents using the new RAG API approach
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

            logger.info(f"🔄 RESET: Resetting batch {batch_id} (#{batch.batch_number} - '{batch.batch_name}') from status {batch.status} to SAVED")

            # Store original status for logging
            original_status = batch.status

            # Reset batch to prestage state
            batch.status = 'SAVED'
            batch.started_at = None  # Clear start time
            batch.completed_at = None  # Clear completion time
            batch.processed_documents = 0  # Reset progress counter

            # Keep total_documents count if it exists (from previous staging)
            # Keep config_snapshot (the batch configuration)
            # Keep folder_ids and meta_data (the batch definition)

            session.commit()

            # Unassign documents from this batch so they can be reassigned during next staging
            documents = session.query(Document).filter(Document.batch_id == batch_id).all()
            documents_unassigned = 0

            for document in documents:
                document.batch_id = None  # Unassign from batch
                documents_unassigned += 1

            session.commit()

            logger.info(f"✅ RESET: Batch {batch_id} reset successfully")
            logger.info(f"   Status: {original_status} → SAVED")
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
                            # Prepare LLM provider data from connection
                            llm_provider_data = {
                                'provider_type': connection.get('provider_type', 'ollama'),
                                'url': connection.get('base_url', 'http://localhost'),
                                'model_name': connection.get('model_name', 'default'),
                                'api_key': connection.get('api_key'),
                                'port_no': connection.get('port_no', 11434)
                            }

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
                                'llm_provider': json.dumps(llm_provider_data),  # Convert to JSON string
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
            
            # Get all batches that are currently ANALYZING
            analyzing_batches = doc_eval_session.query(Batch).filter(
                Batch.status == 'ANALYZING'
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
                                    
                                    # Handle results - could be dict or list
                                    results_raw = status_data.get('results', {})
                                    if isinstance(results_raw, list) and results_raw:
                                        results_data = results_raw[0] if isinstance(results_raw[0], dict) else {}
                                    elif isinstance(results_raw, dict):
                                        results_data = results_raw
                                    else:
                                        results_data = {}
                                    
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
                                    
                                    input_tokens = (
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
                                    
                                    output_tokens = (
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
                                    
                                    time_taken = (
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

# Global instance
batch_service = BatchService()
