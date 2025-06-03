"""
Queue Management Routes for Batch Processing
"""

from flask import Blueprint, jsonify, request
import logging
from services.batch_queue_processor import (
    batch_queue_processor,
    start_queue_processor, 
    stop_queue_processor,
    get_queue_processor_status
)

logger = logging.getLogger(__name__)

queue_bp = Blueprint('queue', __name__)


@queue_bp.route('/api/queue/status', methods=['GET'])
def get_queue_status():
    """Get queue processor status"""
    try:
        status = get_queue_processor_status()
        
        # Add queue statistics
        import psycopg2
        conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        cursor = conn.cursor()
        
        # Get queue counts
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM llm_responses 
            GROUP BY status
        """)
        
        status_counts = dict(cursor.fetchall())
        
        # Get processing statistics
        cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE created_at >= NOW() - INTERVAL '1 hour') as last_hour_total,
                COUNT(*) FILTER (WHERE completed_processing_at >= NOW() - INTERVAL '1 hour') as last_hour_completed
            FROM llm_responses
        """)
        
        hour_stats = cursor.fetchone()
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'success': True,
            'processor': status,
            'queue_counts': status_counts,
            'throughput': {
                'last_hour_total': hour_stats[0] if hour_stats else 0,
                'last_hour_completed': hour_stats[1] if hour_stats else 0
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting queue status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@queue_bp.route('/api/queue/start', methods=['POST'])
def start_queue():
    """Start the queue processor"""
    try:
        if batch_queue_processor.is_running:
            return jsonify({
                'success': False,
                'error': 'Queue processor is already running'
            }), 400
            
        start_queue_processor()
        
        return jsonify({
            'success': True,
            'message': 'Queue processor started',
            'status': get_queue_processor_status()
        })
        
    except Exception as e:
        logger.error(f"Error starting queue: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@queue_bp.route('/api/queue/stop', methods=['POST'])
def stop_queue():
    """Stop the queue processor"""
    try:
        if not batch_queue_processor.is_running:
            return jsonify({
                'success': False,
                'error': 'Queue processor is not running'
            }), 400
            
        stop_queue_processor()
        
        return jsonify({
            'success': True,
            'message': 'Queue processor stopped',
            'status': get_queue_processor_status()
        })
        
    except Exception as e:
        logger.error(f"Error stopping queue: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@queue_bp.route('/api/queue/restart', methods=['POST'])
def restart_queue():
    """Restart the queue processor"""
    try:
        if batch_queue_processor.is_running:
            stop_queue_processor()
            
        start_queue_processor()
        
        return jsonify({
            'success': True,
            'message': 'Queue processor restarted',
            'status': get_queue_processor_status()
        })
        
    except Exception as e:
        logger.error(f"Error restarting queue: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@queue_bp.route('/api/queue/reset-stuck', methods=['POST'])
def reset_stuck_items():
    """Reset stuck processing items"""
    try:
        threshold = request.json.get('threshold_minutes', 30) if request.json else 30
        
        reset_count = batch_queue_processor.process_stuck_items(threshold)
        
        return jsonify({
            'success': True,
            'message': f'Reset {reset_count} stuck items',
            'reset_count': reset_count
        })
        
    except Exception as e:
        logger.error(f"Error resetting stuck items: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


def register_queue_routes(app):
    """Register queue routes with the Flask app"""
    app.register_blueprint(queue_bp)