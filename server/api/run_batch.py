"""
Run Batch API Endpoint
STAGE 2: Execute a prepared batch
"""

import logging
from flask import Blueprint, request, jsonify
from services.batch_service import BatchService

logger = logging.getLogger(__name__)

run_batch_bp = Blueprint('run_batch', __name__)

@run_batch_bp.route('/api/batches/<int:batch_id>/run', methods=['POST'])
def run_batch(batch_id):
    """
    STAGE 2: Start execution of a prepared batch
    
    Args:
        batch_id (int): ID of the batch to run
        
    Returns:
        JSON response with execution results
    """
    try:
        logger.info(f"🚀 API: Starting execution of batch {batch_id}")
        
        batch_service = BatchService()
        result = batch_service.run_batch(batch_id)
        
        if result.get('success'):
            logger.info(f"✅ API: Batch {batch_id} execution started successfully")
            return jsonify({
                'success': True,
                'message': f"Batch {result['batch_number']} execution started",
                'batch': result
            })
        else:
            logger.error(f"❌ API: Failed to start batch {batch_id}: {result.get('error')}")
            return jsonify({
                'success': False,
                'error': result.get('error', 'Unknown error')
            }), 400
            
    except Exception as e:
        logger.error(f"❌ API: Error starting batch {batch_id}: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
