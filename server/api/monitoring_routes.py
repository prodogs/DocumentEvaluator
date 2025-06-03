"""
Monitoring Routes - System health and metrics endpoints
"""

from flask import Blueprint, jsonify
from datetime import datetime, timedelta
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    psutil = None
import logging
from typing import Dict, Any
from database import Session
from models import Batch, Document
import psycopg2

logger = logging.getLogger(__name__)

monitoring_bp = Blueprint('monitoring', __name__)


@monitoring_bp.route('/api/health/detailed', methods=['GET'])
def detailed_health_check():
    """
    Comprehensive health check endpoint with detailed system status.
    
    Returns:
        JSON with detailed health information
    """
    health_status = {
        'timestamp': datetime.now().isoformat(),
        'status': 'healthy',  # Will be updated based on checks
        'services': {},
        'metrics': {},
        'issues': []
    }
    
    # Check KnowledgeSync database (main application database)
    try:
        session = Session()
        from sqlalchemy import text
        session.execute(text("SELECT 1"))
        session.close()
        health_status['services']['knowledgesync_database'] = {
            'status': 'healthy',
            'response_time_ms': 0  # TODO: Measure actual response time
        }
    except Exception as e:
        health_status['services']['knowledgesync_database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
        health_status['issues'].append('KnowledgeSync database connection failed')
    
    # Check KnowledgeDocuments database
    try:
        conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        cursor.close()
        conn.close()
        health_status['services']['knowledge_database'] = {
            'status': 'healthy'
        }
    except Exception as e:
        health_status['services']['knowledge_database'] = {
            'status': 'unhealthy',
            'error': str(e)
        }
        health_status['status'] = 'degraded'
        health_status['issues'].append('KnowledgeDocuments database connection failed')
    
    # System metrics
    if PSUTIL_AVAILABLE:
        health_status['metrics']['system'] = {
            'cpu_percent': psutil.cpu_percent(interval=1),
            'memory_percent': psutil.virtual_memory().percent,
            'disk_percent': psutil.disk_usage('/').percent
        }
        
        # Check for high resource usage
        if health_status['metrics']['system']['cpu_percent'] > 80:
            health_status['issues'].append('High CPU usage detected')
        if health_status['metrics']['system']['memory_percent'] > 85:
            health_status['issues'].append('High memory usage detected')
        if health_status['metrics']['system']['disk_percent'] > 90:
            health_status['issues'].append('Low disk space')
            health_status['status'] = 'unhealthy'
    else:
        health_status['metrics']['system'] = {
            'note': 'System metrics unavailable (psutil not installed)'
        }
    
    return jsonify(health_status)


@monitoring_bp.route('/api/metrics/batches', methods=['GET'])
def batch_metrics():
    """
    Get batch processing metrics.
    
    Returns:
        JSON with batch statistics
    """
    try:
        session = Session()
        
        # Get batch statistics
        total_batches = session.query(Batch).count()
        
        # Batch status distribution
        from sqlalchemy import func
        status_counts = dict(
            session.query(Batch.status, func.count(Batch.id))
            .group_by(Batch.status)
            .all()
        )
        
        # Recent batch performance (last 24 hours)
        yesterday = datetime.now() - timedelta(days=1)
        recent_batches = session.query(Batch).filter(
            Batch.created_at >= yesterday
        ).all()
        
        # Calculate average processing time for completed batches
        completed_recent = [b for b in recent_batches if b.status == 'COMPLETED']
        avg_processing_time = None
        if completed_recent:
            processing_times = []
            for batch in completed_recent:
                if batch.completed_at and batch.created_at:
                    delta = batch.completed_at - batch.created_at
                    processing_times.append(delta.total_seconds())
            if processing_times:
                avg_processing_time = sum(processing_times) / len(processing_times)
        
        # Get failure rate
        failed_count = len([b for b in recent_batches if b.status in ['FAILED', 'FAILED_STAGING']])
        failure_rate = (failed_count / len(recent_batches) * 100) if recent_batches else 0
        
        session.close()
        
        return jsonify({
            'total_batches': total_batches,
            'status_distribution': status_counts,
            'last_24_hours': {
                'total': len(recent_batches),
                'completed': len(completed_recent),
                'failed': failed_count,
                'failure_rate': round(failure_rate, 2),
                'avg_processing_time_seconds': round(avg_processing_time, 2) if avg_processing_time else None
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting batch metrics: {e}")
        return jsonify({'error': str(e)}), 500


@monitoring_bp.route('/api/metrics/processing-queue', methods=['GET'])
def queue_metrics():
    """
    Get processing queue metrics.
    
    Returns:
        JSON with queue statistics
    """
    try:
        # Connect to KnowledgeDocuments to check queue
        conn = psycopg2.connect(
            host="studio.local",
            database="KnowledgeDocuments",
            user="postgres",
            password="prodogs03",
            port=5432
        )
        cursor = conn.cursor()
        
        # Get queue status counts
        cursor.execute("""
            SELECT status, COUNT(*) 
            FROM llm_responses 
            WHERE created_at >= NOW() - INTERVAL '24 hours'
            GROUP BY status
        """)
        
        status_counts = dict(cursor.fetchall())
        
        # Get processing statistics
        cursor.execute("""
            SELECT 
                COUNT(*) FILTER (WHERE status = 'QUEUED') as queued,
                COUNT(*) FILTER (WHERE status = 'PROCESSING') as processing,
                COUNT(*) FILTER (WHERE status = 'COMPLETED') as completed,
                COUNT(*) FILTER (WHERE status = 'FAILED') as failed,
                COUNT(*) as total
            FROM llm_responses
            WHERE created_at >= NOW() - INTERVAL '1 hour'
        """)
        
        hourly_stats = cursor.fetchone()
        
        # Check for stuck items
        cursor.execute("""
            SELECT COUNT(*) 
            FROM llm_responses 
            WHERE status = 'PROCESSING' 
            AND started_processing_at < NOW() - INTERVAL '30 minutes'
        """)
        
        stuck_count = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return jsonify({
            'last_24_hours': status_counts,
            'last_hour': {
                'queued': hourly_stats[0],
                'processing': hourly_stats[1],
                'completed': hourly_stats[2],
                'failed': hourly_stats[3],
                'total': hourly_stats[4],
                'throughput_per_hour': hourly_stats[2]  # Completed in last hour
            },
            'alerts': {
                'stuck_processing': stuck_count,
                'high_failure_rate': hourly_stats[3] / hourly_stats[4] > 0.1 if hourly_stats[4] > 0 else False
            }
        })
        
    except Exception as e:
        logger.error(f"Error getting queue metrics: {e}")
        return jsonify({'error': str(e)}), 500


@monitoring_bp.route('/api/metrics/errors', methods=['GET'])
def error_metrics():
    """
    Get recent errors and issues.
    
    Returns:
        JSON with error information
    """
    try:
        errors = []
        
        # Check for recent batch failures
        session = Session()
        failed_batches = session.query(Batch).filter(
            Batch.status.in_(['FAILED', 'FAILED_STAGING']),
            Batch.updated_at >= datetime.now() - timedelta(hours=24)
        ).all()
        
        for batch in failed_batches:
            errors.append({
                'type': 'batch_failure',
                'batch_id': batch.id,
                'batch_name': batch.batch_name,
                'status': batch.status,
                'timestamp': batch.updated_at.isoformat() if batch.updated_at else None
            })
        
        session.close()
        
        # Check for database errors in KnowledgeDocuments
        try:
            conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            cursor = conn.cursor()
            
            # Get recent failed responses
            cursor.execute("""
                SELECT id, batch_id, error_message, updated_at
                FROM llm_responses
                WHERE status = 'FAILED'
                AND updated_at >= NOW() - INTERVAL '24 hours'
                ORDER BY updated_at DESC
                LIMIT 10
            """)
            
            for row in cursor.fetchall():
                errors.append({
                    'type': 'llm_response_failure',
                    'response_id': row[0],
                    'batch_id': row[1],
                    'error': row[2],
                    'timestamp': row[3].isoformat() if row[3] else None
                })
            
            cursor.close()
            conn.close()
            
        except Exception as e:
            errors.append({
                'type': 'database_error',
                'error': str(e),
                'timestamp': datetime.now().isoformat()
            })
        
        return jsonify({
            'error_count': len(errors),
            'recent_errors': errors
        })
        
    except Exception as e:
        logger.error(f"Error getting error metrics: {e}")
        return jsonify({'error': str(e)}), 500


@monitoring_bp.route('/api/dashboard', methods=['GET'])
def monitoring_dashboard():
    """
    Combined monitoring dashboard data.
    
    Returns:
        JSON with all monitoring data for a dashboard view
    """
    dashboard_data = {
        'timestamp': datetime.now().isoformat(),
        'health': {},
        'metrics': {},
        'alerts': []
    }
    
    # Get health status
    health_response = detailed_health_check()
    dashboard_data['health'] = health_response.get_json()
    
    # Get batch metrics
    batch_response = batch_metrics()
    if batch_response.status_code == 200:
        dashboard_data['metrics']['batches'] = batch_response.get_json()
    
    # Get queue metrics
    queue_response = queue_metrics()
    if queue_response.status_code == 200:
        dashboard_data['metrics']['queue'] = queue_response.get_json()
    
    # Generate alerts based on metrics
    if dashboard_data['health']['status'] != 'healthy':
        dashboard_data['alerts'].append({
            'level': 'critical' if dashboard_data['health']['status'] == 'unhealthy' else 'warning',
            'message': f"System status: {dashboard_data['health']['status']}",
            'details': dashboard_data['health']['issues']
        })
    
    # Check for high failure rates
    if 'batches' in dashboard_data['metrics']:
        failure_rate = dashboard_data['metrics']['batches']['last_24_hours']['failure_rate']
        if failure_rate > 10:
            dashboard_data['alerts'].append({
                'level': 'warning',
                'message': f"High batch failure rate: {failure_rate}%"
            })
    
    # Check for stuck processing
    if 'queue' in dashboard_data['metrics']:
        stuck = dashboard_data['metrics']['queue']['alerts']['stuck_processing']
        if stuck > 0:
            dashboard_data['alerts'].append({
                'level': 'warning',
                'message': f"{stuck} items stuck in processing"
            })
    
    return jsonify(dashboard_data)


def register_monitoring_routes(app):
    """Register monitoring routes with the Flask app."""
    app.register_blueprint(monitoring_bp)