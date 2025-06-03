"""
Simple recovery service that actually works
"""

import logging
from datetime import datetime
import psycopg2

# Handle imports based on how script is run
try:
    from database import Session
    from models import Batch
except ImportError:
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from database import Session
    from models import Batch

logger = logging.getLogger(__name__)

def perform_simple_recovery():
    """
    Simple recovery that finds and fixes stuck batches
    """
    logger.info("=" * 60)
    logger.info("SIMPLE RECOVERY: Starting cleanup of stuck batches")
    logger.info("=" * 60)
    
    session = Session()
    try:
        # Find ALL batches that might be stuck in processing states
        stuck_batches = session.query(Batch).filter(
            Batch.status.in_(['PROCESSING', 'ANALYZING', 'STAGING'])
        ).all()
        
        if not stuck_batches:
            logger.info("✅ No stuck batches found - system is clean!")
            return {"batches_fixed": 0}
        
        logger.warning(f"⚠️  Found {len(stuck_batches)} stuck batches to fix")
        
        fixed_count = 0
        for batch in stuck_batches:
            try:
                logger.info(f"🔧 Fixing batch {batch.id} '{batch.batch_name}' (status: {batch.status})")
                
                # Connect to KnowledgeDocuments to check actual completion
                kb_conn = psycopg2.connect(
                    host="studio.local",
                    database="KnowledgeDocuments",
                    user="postgres",
                    password="prodogs03",
                    port=5432
                )
                kb_cursor = kb_conn.cursor()
                
                # Count completed vs total responses
                kb_cursor.execute("""
                    SELECT 
                        COUNT(*) as total,
                        COUNT(CASE WHEN status IN ('COMPLETED', 'FAILED') THEN 1 END) as done
                    FROM llm_responses 
                    WHERE batch_id = %s
                """, (batch.id,))
                
                result = kb_cursor.fetchone()
                total_responses = result[0]
                done_responses = result[1]
                
                # Also mark any stuck PROCESSING responses as FAILED
                kb_cursor.execute("""
                    UPDATE llm_responses
                    SET status = 'FAILED',
                        error_message = 'Marked as failed by recovery - task was stuck',
                        completed_processing_at = NOW()
                    WHERE batch_id = %s 
                    AND status = 'PROCESSING'
                    AND (started_processing_at < NOW() - INTERVAL '1 hour' 
                         OR started_processing_at IS NULL)
                """, (batch.id,))
                
                stuck_tasks = kb_cursor.rowcount
                if stuck_tasks > 0:
                    logger.info(f"   Marked {stuck_tasks} stuck tasks as FAILED")
                
                kb_conn.commit()
                kb_cursor.close()
                kb_conn.close()
                
                # Decide new status based on actual state
                if total_responses == 0:
                    # No responses - reset to SAVED
                    batch.status = 'SAVED'
                    batch.started_at = None
                    logger.info(f"   ✅ Reset to SAVED (no responses found)")
                elif done_responses == total_responses:
                    # All done - mark as COMPLETED
                    batch.status = 'COMPLETED'
                    batch.completed_at = datetime.now()
                    logger.info(f"   ✅ Marked as COMPLETED ({done_responses}/{total_responses} done)")
                else:
                    # Partially done - reset to STAGED for re-running
                    batch.status = 'STAGED'
                    logger.info(f"   ✅ Reset to STAGED ({done_responses}/{total_responses} done)")
                
                session.commit()
                fixed_count += 1
                
            except Exception as e:
                logger.error(f"   ❌ Error fixing batch {batch.id}: {e}")
                session.rollback()
        
        logger.info(f"✅ Recovery completed - fixed {fixed_count} batches")
        return {"batches_fixed": fixed_count}
        
    except Exception as e:
        logger.error(f"❌ Recovery failed: {e}")
        return {"batches_fixed": 0, "error": str(e)}
    finally:
        session.close()

if __name__ == "__main__":
    # Allow running directly for testing
    logging.basicConfig(level=logging.INFO)
    result = perform_simple_recovery()
    print(f"Recovery result: {result}")