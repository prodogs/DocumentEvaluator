"""
Startup Recovery Service

This service handles recovery of stuck batches and documents when the service starts.
It ensures clean state recovery after unexpected shutdowns or crashes.
"""

import logging
from datetime import datetime
from typing import List, Dict, Any
from sqlalchemy import text
from database import Session
from models import Batch, Document

logger = logging.getLogger(__name__)


class StartupRecoveryService:
    """Handles recovery of stuck processing states on service startup"""
    
    def __init__(self):
        self.recovered_batches = []
        self.recovered_documents = []
        self.recovered_tasks = []
        
    def perform_recovery(self) -> Dict[str, Any]:
        """
        Perform all recovery operations on startup.
        Returns a summary of recovery actions taken.
        """
        logger.info("=" * 60)
        logger.info("Starting recovery process for stuck batches and documents")
        logger.info("=" * 60)
        
        recovery_summary = {
            'start_time': datetime.now(),
            'batches_recovered': 0,
            'documents_recovered': 0,
            'tasks_recovered': 0,
            'errors': []
        }
        
        try:
            # Recover stuck batches
            batch_count = self._recover_stuck_batches()
            recovery_summary['batches_recovered'] = batch_count
            
            # Recover stuck documents
            doc_count = self._recover_stuck_documents()
            recovery_summary['documents_recovered'] = doc_count
            
            # Recover orphaned tasks
            task_count = self._recover_orphaned_tasks()
            recovery_summary['tasks_recovered'] = task_count
            
            recovery_summary['end_time'] = datetime.now()
            recovery_summary['duration'] = (recovery_summary['end_time'] - recovery_summary['start_time']).total_seconds()
            
            logger.info("=" * 60)
            logger.info(f"Recovery completed in {recovery_summary['duration']:.2f} seconds")
            logger.info(f"Batches recovered: {batch_count}")
            logger.info(f"Documents recovered: {doc_count}")
            logger.info(f"Tasks recovered: {task_count}")
            logger.info("=" * 60)
            
        except Exception as e:
            logger.error(f"Error during recovery process: {e}")
            recovery_summary['errors'].append(str(e))
            
        return recovery_summary
    
    def _recover_stuck_batches(self) -> int:
        """
        Recover batches stuck in ANALYZING status from previous sessions.
        These batches should be reset to STAGED for re-processing or marked as
        COMPLETED if all documents are done.
        """
        session = Session()
        recovered_count = 0
        
        try:
            # Find batches stuck in ANALYZING, STAGING, or PROCESSING status
            stuck_batches = session.query(Batch).filter(
                Batch.status.in_(['ANALYZING', 'STAGING', 'PROCESSING'])
            ).all()
            
            if not stuck_batches:
                logger.info("No stuck batches found in ANALYZING, STAGING, or PROCESSING status")
                return 0
            
            logger.warning(f"Found {len(stuck_batches)} batches stuck in ANALYZING/STAGING/PROCESSING status")
            
            for batch in stuck_batches:
                try:
                    batch_id = batch.id
                    batch_name = batch.batch_name
                    batch_status = batch.status
                    started_at = batch.started_at
                    
                    # Handle STAGING status - reset to SAVED
                    if batch_status == 'STAGING':
                        batch.status = 'SAVED'
                        batch.started_at = None
                        logger.info(f"Batch {batch_id} '{batch_name}' reset from STAGING to SAVED")
                        self.recovered_batches.append({
                            'batch_id': batch_id,
                            'batch_name': batch_name,
                            'action': 'RESET_TO_SAVED',
                            'previous_status': 'STAGING'
                        })
                        recovered_count += 1
                        continue
                    
                    # For ANALYZING or PROCESSING status, check document completion
                    # Connect to KnowledgeDocuments database for llm_responses
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
                        
                        # Check completed documents
                        kb_cursor.execute("""
                            SELECT COUNT(*) 
                            FROM llm_responses 
                            WHERE batch_id = %s 
                            AND status = 'COMPLETED'
                        """, (batch_id,))
                        completed_docs = kb_cursor.fetchone()[0]
                        
                        # Check total documents expected
                        kb_cursor.execute("""
                            SELECT COUNT(*) 
                            FROM llm_responses 
                            WHERE batch_id = %s
                        """, (batch_id,))
                        total_docs = kb_cursor.fetchone()[0]
                        
                        kb_cursor.close()
                        kb_conn.close()
                    except Exception as kb_error:
                        logger.error(f"Error checking KnowledgeDocuments for batch {batch_id}: {kb_error}")
                        completed_docs = 0
                        total_docs = 0
                    
                    if completed_docs == total_docs and total_docs > 0:
                        # All documents completed, mark batch as COMPLETED
                        batch.status = 'COMPLETED'
                        batch.completed_at = datetime.now()
                        logger.info(f"Batch {batch_id} '{batch_name}' recovered as COMPLETED ({completed_docs}/{total_docs} docs)")
                    else:
                        # Reset to STAGED for re-processing
                        batch.status = 'STAGED'
                        batch.started_at = None
                        batch.completed_at = None
                        
                        # Reset any PROCESSING documents to QUEUED
                        session.execute(text("""
                            UPDATE llm_responses
                            SET status = 'QUEUED',
                                task_id = NULL,
                                started_processing_at = NULL
                            WHERE batch_id = :batch_id 
                            AND status = 'PROCESSING'
                        """), {'batch_id': batch_id})
                        
                        logger.info(f"Batch {batch_id} '{batch_name}' reset to STAGED ({completed_docs}/{total_docs} docs completed)")
                    
                    self.recovered_batches.append({
                        'batch_id': batch_id,
                        'batch_name': batch_name,
                        'action': 'COMPLETED' if completed_docs == total_docs else 'RESET_TO_STAGED',
                        'completed_docs': completed_docs,
                        'total_docs': total_docs
                    })
                    
                    recovered_count += 1
                    
                except Exception as e:
                    logger.error(f"Error recovering batch {batch.id}: {e}")
                    
            session.commit()
            
        except Exception as e:
            logger.error(f"Error during batch recovery: {e}")
            session.rollback()
        finally:
            session.close()
            
        return recovered_count
    
    def _recover_stuck_documents(self) -> int:
        """
        Recover documents stuck in PROCESSING status without active tasks.
        """
        session = Session()
        recovered_count = 0
        
        try:
            # Connect to KnowledgeDocuments database to update llm_responses
            import psycopg2
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Find documents stuck in PROCESSING without task_id or with old task_ids
            kb_cursor.execute("""
                UPDATE llm_responses
                SET status = 'QUEUED',
                    task_id = NULL,
                    started_processing_at = NULL,
                    error_message = 'Reset from PROCESSING on startup recovery'
                WHERE status = 'PROCESSING'
                AND (
                    task_id IS NULL 
                    OR task_id = ''
                    OR started_processing_at < NOW() - INTERVAL '1 hour'
                )
                RETURNING id, document_id, batch_id
            """)
            
            recovered_docs = kb_cursor.fetchall()
            recovered_count = kb_cursor.rowcount
            
            if recovered_count > 0:
                logger.info(f"Reset {recovered_count} stuck documents from PROCESSING to QUEUED")
                for doc in recovered_docs:
                    self.recovered_documents.append({
                        'response_id': doc[0],
                        'document_id': doc[1],
                        'batch_id': doc[2],
                        'action': 'RESET_TO_QUEUED'
                    })
            else:
                logger.info("No stuck documents found in PROCESSING status")
                
            kb_conn.commit()
            kb_cursor.close()
            kb_conn.close()
            
        except Exception as e:
            logger.error(f"Error during document recovery: {e}")
            if 'kb_conn' in locals():
                kb_conn.rollback()
                kb_conn.close()
        finally:
            session.close()
            
        return recovered_count
    
    def _recover_orphaned_tasks(self) -> int:
        """
        Recover tasks that have task_ids but may be orphaned from the RAG API.
        This identifies tasks that need monitoring by the batch queue processor.
        """
        session = Session()
        recovered_count = 0
        
        try:
            # Connect to KnowledgeDocuments database to check for orphaned tasks
            import psycopg2
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Find documents with task_ids that are still PROCESSING
            # These will be picked up by the batch_queue_processor's recovery logic
            kb_cursor.execute("""
                SELECT COUNT(*)
                FROM llm_responses
                WHERE status = 'PROCESSING'
                AND task_id IS NOT NULL
                AND task_id != ''
            """)
            orphaned_tasks = kb_cursor.fetchone()[0]
            
            kb_cursor.close()
            kb_conn.close()
            
            if orphaned_tasks > 0:
                logger.info(f"Found {orphaned_tasks} tasks with task_ids that will be monitored for completion")
                recovered_count = orphaned_tasks
            else:
                logger.info("No orphaned tasks found")
                
        except Exception as e:
            logger.error(f"Error checking for orphaned tasks: {e}")
        finally:
            session.close()
            
        return recovered_count
    
    def get_recovery_summary(self) -> Dict[str, Any]:
        """Get a summary of the recovery actions taken"""
        return {
            'recovered_batches': self.recovered_batches,
            'recovered_documents': self.recovered_documents,
            'recovered_tasks': self.recovered_tasks,
            'total_recovered': {
                'batches': len(self.recovered_batches),
                'documents': len(self.recovered_documents),
                'tasks': len(self.recovered_tasks)
            }
        }


# Global instance
startup_recovery = StartupRecoveryService()


def perform_startup_recovery():
    """Perform startup recovery - called when the service starts"""
    return startup_recovery.perform_recovery()


def get_recovery_summary():
    """Get summary of last recovery operation"""
    return startup_recovery.get_recovery_summary()