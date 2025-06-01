"""
Batch Archive Service

Handles archiving and deletion of batches with complete data preservation.
Archives batch, documents, and LLM responses data to JSON before deletion.
"""

import logging
import json
from datetime import datetime
from typing import Optional, Dict, Any, List
from sqlalchemy.orm import joinedload
from models import Batch, Document, LlmResponse, BatchArchive, Folder, Prompt, Connection
from database import Session

logger = logging.getLogger(__name__)

class BatchArchiveService:
    """Service for archiving and deleting batches with data preservation"""

    def archive_and_delete_batch(self, batch_id: int, archived_by: Optional[str] = None, archive_reason: Optional[str] = None) -> Dict[str, Any]:
        """
        Archive a batch and all its associated data, then delete from main tables

        Args:
            batch_id (int): ID of the batch to archive and delete
            archived_by (str, optional): Who is performing the archival
            archive_reason (str, optional): Reason for archival

        Returns:
            Dict[str, Any]: Result of the archival operation
        """
        session = Session()
        try:
            # Get the batch with all related data
            batch = session.query(Batch).filter(Batch.id == batch_id).first()
            if not batch:
                return {
                    'success': False,
                    'error': f'Batch {batch_id} not found'
                }

            # Check if batch is currently processing
            if batch.status == 'P':
                return {
                    'success': False,
                    'error': f'Cannot delete batch {batch_id} - it is currently processing'
                }

            # Get all documents associated with this batch
            documents = session.query(Document).options(
                joinedload(Document.folder)
            ).filter(Document.batch_id == batch_id).all()

            # Get all LLM responses for documents in this batch
            # Using raw query to avoid schema mismatch issues with LlmConfiguration model
            llm_response_ids = session.query(LlmResponse.id).join(Document).filter(Document.batch_id == batch_id).all()
            llm_response_ids = [r[0] for r in llm_response_ids]

            # Load responses individually to avoid relationship issues
            llm_responses = []
            for response_id in llm_response_ids:
                response = session.query(LlmResponse).options(
                    joinedload(LlmResponse.prompt)
                ).filter(LlmResponse.id == response_id).first()
                if response:
                    llm_responses.append(response)

            # Serialize batch data
            batch_data = self._serialize_batch(batch)

            # Serialize documents data
            documents_data = [self._serialize_document(doc) for doc in documents]

            # Serialize LLM responses data
            llm_responses_data = [self._serialize_llm_response(resp) for resp in llm_responses]

            # Create metadata
            metadata = {
                'total_documents': len(documents),
                'total_responses': len(llm_responses),
                'response_status_counts': self._count_response_statuses(llm_responses),
                'archived_at_timestamp': datetime.now().isoformat(),
                'folder_ids': batch.folder_ids if batch.folder_ids else [],
                'completion_percentage': batch_data.get('completion_percentage', 0)
            }

            # Create archive record
            archive = BatchArchive(
                original_batch_id=batch_id,
                batch_number=batch.batch_number,
                batch_name=batch.batch_name,
                archived_by=archived_by or 'System',
                archive_reason=archive_reason or 'Manual deletion',
                batch_data=batch_data,
                documents_data=documents_data,
                llm_responses_data=llm_responses_data,
                archive_metadata=metadata
            )

            session.add(archive)
            session.flush()  # Get the archive ID

            # Delete LLM responses first (due to foreign key constraints)
            for response in llm_responses:
                session.delete(response)

            # Delete documents
            for document in documents:
                session.delete(document)

            # Delete the batch
            session.delete(batch)

            # Commit all changes
            session.commit()

            logger.info(f"Successfully archived and deleted batch {batch_id} (#{batch.batch_number})")

            return {
                'success': True,
                'message': f'Batch #{batch.batch_number} archived and deleted successfully',
                'archive_id': archive.id,
                'archived_data': {
                    'batch_name': batch.batch_name,
                    'batch_number': batch.batch_number,
                    'total_documents': len(documents),
                    'total_responses': len(llm_responses),
                    'archived_at': archive.archived_at.isoformat() if archive.archived_at else None
                }
            }

        except Exception as e:
            session.rollback()
            logger.error(f"Error archiving batch {batch_id}: {e}", exc_info=True)
            return {
                'success': False,
                'error': f'Failed to archive batch: {str(e)}'
            }
        finally:
            session.close()

    def _serialize_batch(self, batch: Batch) -> Dict[str, Any]:
        """Serialize batch object to dictionary"""
        return {
            'id': batch.id,
            'batch_number': batch.batch_number,
            'batch_name': batch.batch_name,
            'description': batch.description,
            'folder_path': batch.folder_path,
            'folder_ids': batch.folder_ids,
            'meta_data': batch.meta_data,
            'status': batch.status,
            'total_documents': batch.total_documents,
            'processed_documents': batch.processed_documents,
            'created_at': batch.created_at.isoformat() if batch.created_at else None,
            'started_at': batch.started_at.isoformat() if batch.started_at else None,
            'completed_at': batch.completed_at.isoformat() if batch.completed_at else None
        }

    def _serialize_document(self, document: Document) -> Dict[str, Any]:
        """Serialize document object to dictionary"""
        return {
            'id': document.id,
            'filepath': document.filepath,
            'filename': document.filename,
            'folder_id': document.folder_id,
            'batch_id': document.batch_id,
            'task_id': document.task_id,
            'created_at': document.created_at.isoformat() if document.created_at else None,
            'folder': {
                'id': document.folder.id,
                'folder_path': document.folder.folder_path,
                'folder_name': document.folder.folder_name,
                'active': document.folder.active
            } if document.folder else None
        }

    def _serialize_llm_response(self, response: LlmResponse) -> Dict[str, Any]:
        """Serialize LLM response object to dictionary"""
        # Get connection data instead of deprecated llm_config
        connection_data = None
        if response.connection_id:
            try:
                # Query connection data with provider and model info
                from database import Session
                from sqlalchemy import text
                session = Session()
                connection = session.execute(text("""
                    SELECT c.id, c.name, c.description, c.base_url, c.api_key, c.port_no,
                           c.is_active, c.created_at, p.provider_type, m.display_name as model_name
                    FROM connections c
                    LEFT JOIN llm_providers p ON c.provider_id = p.id
                    LEFT JOIN models m ON c.model_id = m.id
                    WHERE c.id = :connection_id
                """), {'connection_id': response.connection_id}).fetchone()

                if connection:
                    connection_data = {
                        'id': connection[0],
                        'name': connection[1],
                        'description': connection[2],
                        'base_url': connection[3],
                        'api_key': connection[4],
                        'port_no': connection[5],
                        'is_active': connection[6],
                        'created_at': connection[7].isoformat() if connection[7] else None,
                        'provider_type': connection[8],
                        'model_name': connection[9]
                    }
                session.close()
            except Exception as e:
                logger.warning(f"Could not load connection {response.connection_id}: {e}")

        return {
            'id': response.id,
            'document_id': response.document_id,
            'prompt_id': response.prompt_id,
            'connection_id': response.connection_id,
            'task_id': response.task_id,
            'status': response.status,
            'response_json': response.response_json,
            'response_text': response.response_text,
            'response_time_ms': response.response_time_ms,
            'error_message': response.error_message,
            'started_processing_at': response.started_processing_at.isoformat() if response.started_processing_at else None,
            'completed_processing_at': response.completed_processing_at.isoformat() if response.completed_processing_at else None,
            'timestamp': response.timestamp.isoformat() if response.timestamp else None,
            'prompt': {
                'id': response.prompt.id,
                'prompt_text': response.prompt.prompt_text,
                'description': response.prompt.description,
                'active': response.prompt.active
            } if response.prompt else None,
            'connection': connection_data
        }

    def _count_response_statuses(self, responses: List[LlmResponse]) -> Dict[str, int]:
        """Count responses by status"""
        counts = {}
        for response in responses:
            status = response.status
            counts[status] = counts.get(status, 0) + 1
        return counts

    def list_archived_batches(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        List archived batches with summary information

        Args:
            limit (int): Maximum number of archived batches to return

        Returns:
            List[Dict[str, Any]]: List of archived batch summaries
        """
        session = Session()
        try:
            archives = session.query(BatchArchive).order_by(
                BatchArchive.archived_at.desc()
            ).limit(limit).all()

            archive_list = []
            for archive in archives:
                archive_list.append({
                    'archive_id': archive.id,
                    'original_batch_id': archive.original_batch_id,
                    'batch_number': archive.batch_number,
                    'batch_name': archive.batch_name,
                    'archived_at': archive.archived_at.isoformat() if archive.archived_at else None,
                    'archived_by': archive.archived_by,
                    'archive_reason': archive.archive_reason,
                    'metadata': archive.archive_metadata
                })

            return archive_list

        except Exception as e:
            logger.error(f"Error listing archived batches: {e}", exc_info=True)
            return []
        finally:
            session.close()

    def get_archived_batch(self, archive_id: int) -> Optional[Dict[str, Any]]:
        """
        Get complete archived batch data

        Args:
            archive_id (int): ID of the archive record

        Returns:
            Dict[str, Any]: Complete archived batch data or None if not found
        """
        session = Session()
        try:
            archive = session.query(BatchArchive).filter(BatchArchive.id == archive_id).first()
            if not archive:
                return None

            return {
                'archive_id': archive.id,
                'original_batch_id': archive.original_batch_id,
                'batch_number': archive.batch_number,
                'batch_name': archive.batch_name,
                'archived_at': archive.archived_at.isoformat() if archive.archived_at else None,
                'archived_by': archive.archived_by,
                'archive_reason': archive.archive_reason,
                'batch_data': archive.batch_data,
                'documents_data': archive.documents_data,
                'llm_responses_data': archive.llm_responses_data,
                'metadata': archive.archive_metadata
            }

        except Exception as e:
            logger.error(f"Error getting archived batch {archive_id}: {e}", exc_info=True)
            return None
        finally:
            session.close()

# Global instance
batch_archive_service = BatchArchiveService()
