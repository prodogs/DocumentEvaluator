"""
Batch Management API Routes

Provides REST API endpoints for managing document processing batches:
- List batches
- Get batch details
- Update batch names
- Monitor batch progress
"""

import logging
from datetime import datetime
from flask import Blueprint, request, jsonify
from server.services.batch_service import batch_service
from server.services.batch_archive_service import batch_archive_service
from server.services.batch_cleanup_service import batch_cleanup_service

logger = logging.getLogger(__name__)

def register_batch_routes(app):
    """Register batch management routes with the Flask app"""

    @app.route('/api/batches', methods=['GET'])
    def list_batches():
        """List all batches with summary information"""
        try:
            limit = request.args.get('limit', 50, type=int)
            batches = batch_service.list_batches(limit=limit)

            return jsonify({
                'success': True,
                'batches': batches,
                'count': len(batches)
            })

        except Exception as e:
            logger.error(f"Error listing batches: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>', methods=['GET'])
    def get_batch_details(batch_id):
        """Get detailed information about a specific batch"""
        try:
            batch_info = batch_service.get_batch_info(batch_id)

            if not batch_info:
                return jsonify({
                    'success': False,
                    'error': f'Batch {batch_id} not found'
                }), 404

            return jsonify({
                'success': True,
                'batch': batch_info
            })

        except Exception as e:
            logger.error(f"Error getting batch details {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>/name', methods=['PUT'])
    def update_batch_name(batch_id):
        """Update the name and description of a batch"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'Request body is required'
                }), 400

            batch_name = data.get('batch_name')
            description = data.get('description')

            if not batch_name:
                return jsonify({
                    'success': False,
                    'error': 'batch_name is required'
                }), 400

            success = batch_service.update_batch_name(batch_id, batch_name, description)

            if not success:
                return jsonify({
                    'success': False,
                    'error': f'Failed to update batch {batch_id}'
                }), 404

            # Get updated batch info
            batch_info = batch_service.get_batch_info(batch_id)

            return jsonify({
                'success': True,
                'message': f'Batch {batch_id} updated successfully',
                'batch': batch_info
            })

        except Exception as e:
            logger.error(f"Error updating batch name {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>/progress', methods=['GET'])
    def get_batch_progress(batch_id):
        """Get current progress of a batch"""
        try:
            progress = batch_service.update_batch_progress(batch_id)

            if not progress:
                return jsonify({
                    'success': False,
                    'error': f'Batch {batch_id} not found'
                }), 404

            return jsonify({
                'success': True,
                'progress': progress
            })

        except Exception as e:
            logger.error(f"Error getting batch progress {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/current', methods=['GET'])
    def get_current_batch():
        """Get the currently processing batch"""
        try:
            from server.services.batch_service import batch_service
            current_batch = batch_service.get_current_batch()

            if not current_batch:
                return jsonify({
                    'success': True,
                    'current_batch': None,
                    'message': 'No batch currently processing'
                })

            # Get detailed info for the current batch
            batch_info = batch_service.get_batch_info(current_batch.id)

            return jsonify({
                'success': True,
                'current_batch': batch_info
            })

        except Exception as e:
            logger.error(f"Error getting current batch: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/stats', methods=['GET'])
    def get_batch_stats():
        """Get comprehensive batch processing statistics"""
        try:
            stats = batch_service.get_batch_summary_stats()

            return jsonify({
                'success': True,
                'stats': stats
            })

        except Exception as e:
            logger.error(f"Error getting batch stats: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>/real-time-progress', methods=['GET'])
    def get_real_time_batch_progress(batch_id):
        """Get comprehensive real-time progress for a specific batch"""
        try:
            progress = batch_service.get_real_time_batch_progress(batch_id)

            if not progress:
                return jsonify({
                    'success': False,
                    'error': f'Batch {batch_id} not found'
                }), 404

            return jsonify({
                'success': True,
                'progress': progress
            })

        except Exception as e:
            logger.error(f"Error getting real-time batch progress {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/active/progress', methods=['GET'])
    def get_all_active_batches_progress():
        """Get real-time progress for all active batches"""
        try:
            progress_list = batch_service.get_all_active_batches_progress()

            return jsonify({
                'success': True,
                'active_batches': progress_list,
                'count': len(progress_list)
            })

        except Exception as e:
            logger.error(f"Error getting all active batches progress: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/dashboard', methods=['GET'])
    def get_batch_dashboard():
        """Get comprehensive dashboard data for batch processing"""
        try:
            # Check if specific batch IDs are requested
            batch_ids_param = request.args.get('batch_ids')
            batch_ids = None
            if batch_ids_param:
                try:
                    batch_ids = [int(id.strip()) for id in batch_ids_param.split(',') if id.strip()]
                except ValueError:
                    return jsonify({
                        'success': False,
                        'error': 'Invalid batch_ids parameter. Must be comma-separated integers.'
                    }), 400

            # Get active batches progress first
            active_batches = batch_service.get_all_active_batches_progress()

            # Determine which batches to show stats for
            stats_batch_ids = batch_ids  # Use provided batch_ids if specified
            stats_context = 'filtered'

            if not batch_ids:  # No specific batch IDs requested
                if active_batches:  # There are active batches
                    # Show stats only for active batches
                    stats_batch_ids = [batch['batch_id'] for batch in active_batches]
                    stats_context = 'active_only'
                else:
                    # No active batches, show stats for all batches
                    stats_batch_ids = None
                    stats_context = 'all_batches'

            # Get summary stats (filtered appropriately)
            summary_stats = batch_service.get_batch_summary_stats(batch_ids=stats_batch_ids)

            # Add context information to summary stats
            summary_stats['stats_context'] = stats_context
            if stats_context == 'active_only':
                summary_stats['active_batch_ids'] = stats_batch_ids

            # Get recent batches (last 10)
            recent_batches = batch_service.list_batches(limit=10)

            return jsonify({
                'success': True,
                'dashboard': {
                    'summary_stats': summary_stats,
                    'active_batches': active_batches,
                    'recent_batches': recent_batches,
                    'last_updated': datetime.now().isoformat(),
                    'filtered_batch_ids': batch_ids
                }
            })

        except Exception as e:
            logger.error(f"Error getting batch dashboard: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>/config-snapshot', methods=['GET'])
    def get_batch_config_snapshot(batch_id):
        """Get the configuration snapshot for a specific batch"""
        try:
            from server.database import Session
            from server.models import Batch

            session = Session()
            try:
                batch = session.query(Batch).filter_by(id=batch_id).first()

                if not batch:
                    return jsonify({
                        'success': False,
                        'error': f'Batch {batch_id} not found'
                    }), 404

                if not batch.config_snapshot:
                    return jsonify({
                        'success': False,
                        'error': f'Batch {batch_id} does not have a configuration snapshot'
                    }), 404

                return jsonify({
                    'success': True,
                    'batch_id': batch_id,
                    'batch_name': batch.batch_name,
                    'batch_number': batch.batch_number,
                    'config_snapshot': batch.config_snapshot
                }), 200

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error getting batch config snapshot: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>/pause', methods=['POST'])
    def pause_batch(batch_id):
        """Pause a batch - stops new documents from being submitted but allows current processing to continue"""
        try:
            result = batch_service.pause_batch(batch_id)

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error pausing batch {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>/resume', methods=['POST'])
    def resume_batch(batch_id):
        """Resume a paused batch - allows new documents to be submitted for processing"""
        try:
            result = batch_service.resume_batch(batch_id)

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error resuming batch {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>', methods=['DELETE'])
    def delete_batch(batch_id):
        """Archive and delete a batch with all associated data"""
        try:
            data = request.get_json() or {}
            archived_by = data.get('archived_by', 'User')
            archive_reason = data.get('archive_reason', 'Manual deletion via UI')

            result = batch_archive_service.archive_and_delete_batch(
                batch_id=batch_id,
                archived_by=archived_by,
                archive_reason=archive_reason
            )

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error deleting batch {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/archived', methods=['GET'])
    def list_archived_batches():
        """List archived batches"""
        try:
            limit = request.args.get('limit', 50, type=int)
            archived_batches = batch_archive_service.list_archived_batches(limit=limit)

            return jsonify({
                'success': True,
                'archived_batches': archived_batches,
                'count': len(archived_batches)
            })

        except Exception as e:
            logger.error(f"Error listing archived batches: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/archived/<int:archive_id>', methods=['GET'])
    def get_archived_batch(archive_id):
        """Get complete archived batch data"""
        try:
            archived_batch = batch_archive_service.get_archived_batch(archive_id)

            if not archived_batch:
                return jsonify({
                    'success': False,
                    'error': f'Archived batch {archive_id} not found'
                }), 404

            return jsonify({
                'success': True,
                'archived_batch': archived_batch
            })

        except Exception as e:
            logger.error(f"Error getting archived batch {archive_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/cleanup', methods=['POST'])
    def manual_cleanup_batches():
        """Manually trigger cleanup of stale batches"""
        try:
            result = batch_cleanup_service.manual_cleanup_all_stale_batches()
            return jsonify(result), 200 if result['success'] else 400

        except Exception as e:
            logger.error(f"Error in manual batch cleanup: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/cleanup/status', methods=['GET'])
    def get_cleanup_status():
        """Get batch cleanup service status"""
        try:
            status = batch_cleanup_service.get_cleanup_status()
            return jsonify(status), 200

        except Exception as e:
            logger.error(f"Error getting cleanup status: {e}", exc_info=True)
            return jsonify({
                'error': str(e)
            }), 500

    logger.info("Batch management routes registered")

# Example usage in app_launcher.py:
# from server.api.batch_routes import register_batch_routes
# register_batch_routes(app)
