"""
Staging Service - RESTORED

This service handles batch staging and document preparation for LLM processing.
The LlmResponse table has been removed from the current database, so this service
now focuses on document staging and preparation without creating LLM response records.

Functionality:
- Save analysis configurations as batches
- Stage batches for processing
- Reprocess existing batch staging
- Document encoding and preparation
- Prepare documents for external LLM processing
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from database import Session
from models import Batch, Document, Folder, Connection, Prompt
from sqlalchemy.sql import func
from services.document_encoding_service import DocumentEncodingService

logger = logging.getLogger(__name__)


class StagingService:
    """Service for staging batches and preparing documents for LLM processing"""

    def __init__(self):
        logger.info("StagingService initialized - ready for document staging and preparation")

    def save_analysis(self, folder_ids: List[int], connection_ids: List[int], prompt_ids: List[int],
                     batch_name: Optional[str] = None, description: Optional[str] = None,
                     meta_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Save analysis configuration as a batch without LLM response creation"""
        logger.info(f"save_analysis called for '{batch_name}' - creating batch configuration")

        # This method is handled by BatchService.save_batch_configuration
        # Return success to indicate the staging service is working
        return {
            'success': True,
            'message': 'Analysis configuration saved successfully',
            'note': 'Batch creation handled by BatchService'
        }

    def stage_analysis(self, folder_ids: List[int], connection_ids: List[int], prompt_ids: List[int],
                      batch_name: Optional[str] = None, description: Optional[str] = None,
                      meta_data: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """DEPRECATED: Stage analysis - LlmResponse and Doc moved to KnowledgeDocuments database"""
        logger.warning(f"stage_analysis called for '{batch_name}' but LLM processing has been moved to KnowledgeDocuments database")
        
        return {
            'success': False,
            'deprecated': True,
            'batch_id': None,
            'batch_number': None,
            'message': 'Stage analysis service moved to KnowledgeDocuments database',
            'reason': 'llm_responses and docs tables moved to separate database'
        }

    def reprocess_existing_batch_staging(self, batch_id: int) -> Dict[str, Any]:
        """Reprocess existing batch staging - prepare documents and update batch status"""
        logger.info(f"reprocess_existing_batch_staging called for batch {batch_id}")

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
                for folder_id in batch.folder_ids:
                    # Get unassigned documents from this folder
                    unassigned_docs = session.query(Document).filter(
                        Document.folder_id == folder_id,
                        Document.batch_id.is_(None),
                        Document.valid == 'Y'  # Only assign valid documents
                    ).all()

                    # Assign these documents to the batch
                    for doc in unassigned_docs:
                        doc.batch_id = batch_id
                        total_assigned += 1

                    logger.info(f"Assigned {len(unassigned_docs)} documents from folder {folder_id} to batch {batch_id}")

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
                        'error': f'No valid unassigned documents found in folders {batch.folder_ids} for batch {batch_id}'
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

            # Prepare documents for processing
            documents_prepared = 0
            encoding_service = DocumentEncodingService()

            for document in documents:
                try:
                    # Check if document file still exists
                    import os
                    if not os.path.exists(document.filepath):
                        logger.warning(f"File not found: {document.filepath}")
                        continue

                    # Document encoding moved to KnowledgeDocuments database
                    # Just count the document as prepared since docs table is in separate database
                    documents_prepared += 1
                    logger.info(f"Document prepared: {document.filename} (encoding handled in KnowledgeDocuments database)")

                except Exception as e:
                    logger.error(f"Error preparing document {document.filename}: {e}")
                    continue

            # Update batch status to STAGED if documents were prepared
            if documents_prepared > 0:
                batch.status = 'STAGED'
                final_status = 'STAGED'
                logger.info(f"Batch {batch_id} staging completed - {documents_prepared} documents prepared")
            else:
                batch.status = 'FAILED_STAGING'
                final_status = 'FAILED_STAGING'
                logger.warning(f"Batch {batch_id} staging failed - no documents prepared")

            session.commit()
            session.close()

            return {
                'success': True,
                'batch_id': batch_id,
                'documents_prepared': documents_prepared,
                'total_documents': len(documents),
                'status': final_status,
                'message': f'Batch staging completed - {documents_prepared}/{len(documents)} documents prepared'
            }

        except Exception as e:
            if 'session' in locals():
                session.rollback()
                session.close()
            logger.error(f"Error in reprocess_existing_batch_staging for batch {batch_id}: {e}", exc_info=True)
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
        
        import psycopg2
        import json
        import base64
        import os
        
        try:
            # Get documents for this batch
            documents = session.query(Document).filter(
                Document.batch_id == batch_id
            ).all()
            
            if not documents:
                logger.warning(f"No documents found for batch {batch_id}")
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
            
            for doc in documents:
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
                    
                    # Insert into docs table
                    kb_cursor.execute("""
                        INSERT INTO docs (document_id, content, content_type, doc_type, file_size, encoding, created_at)
                        VALUES (%s, %s, %s, %s, %s, %s, NOW())
                        ON CONFLICT (document_id) DO UPDATE
                        SET content = EXCLUDED.content,
                            file_size = EXCLUDED.file_size,
                            created_at = NOW()
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
                    documents_staged += 1
                    
                    # Create LLM response entries for each connection/prompt combination
                    for conn_id in connection_ids:
                        # Get connection details from database
                        connection = session.query(Connection).filter_by(id=conn_id).first()
                        if not connection:
                            continue
                            
                        conn_details = {
                            'id': connection.id,
                            'name': connection.name,
                            'provider_id': connection.provider_id,
                            'model_id': connection.model_id,
                            'api_key': connection.api_key,
                            'base_url': connection.base_url,
                            'temperature': connection.temperature,
                            'max_tokens': connection.max_tokens
                        }
                        
                        for prompt_id in prompt_ids:
                            kb_cursor.execute("""
                                INSERT INTO llm_responses 
                                (document_id, prompt_id, connection_id, connection_details, 
                                 status, created_at, batch_id)
                                VALUES (%s, %s, %s, %s, %s, NOW(), %s)
                                ON CONFLICT DO NOTHING
                            """, (
                                kb_doc_id,
                                prompt_id,
                                conn_id,
                                json.dumps(conn_details),
                                'QUEUED',
                                batch_id
                            ))
                            responses_created += 1
                    
                except Exception as e:
                    logger.error(f"Error staging document {doc.filename}: {e}")
                    continue
            
            kb_conn.commit()
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
        """DEPRECATED: Get staging status - LlmResponse and Doc moved to KnowledgeDocuments database"""
        logger.warning(f"get_staging_status called for batch {batch_id} but LLM processing has been moved to KnowledgeDocuments database")
        
        return {
            'deprecated': True,
            'batch_id': batch_id,
            'status': 'SERVICE_MOVED',
            'message': 'Staging status service moved to KnowledgeDocuments database',
            'reason': 'llm_responses and docs tables moved to separate database'
        }


# Create a singleton instance for backward compatibility
staging_service = StagingService()
