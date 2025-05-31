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
from services.batch_service import batch_service
from services.batch_archive_service import batch_archive_service
from services.batch_cleanup_service import batch_cleanup_service
from services.staging_service import staging_service

logger = logging.getLogger(__name__)

def register_batch_routes(app):
    """Register batch management routes with the Flask app"""

    @app.route('/api/batches/save', methods=['POST'])
    def save_analysis():
        """Save analysis configuration as a batch with SAVED status"""
        try:
            data = request.get_json()
            logger.info(f"📥 Received batch save request with data: {data}")

            if not data:
                logger.error("❌ No data provided in request")
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400

            batch_name = data.get('batch_name')
            folder_ids = data.get('folder_ids', [])
            connection_ids = data.get('connection_ids', [])  # ✅ FIX: Accept selected connections
            llm_config_ids = data.get('llm_config_ids', [])  # ✅ FIX: Accept legacy llm_config_ids
            prompt_ids = data.get('prompt_ids', [])  # ✅ FIX: Accept selected prompts
            meta_data = data.get('meta_data')

            # ✅ FIX: Support both connection_ids and llm_config_ids for backward compatibility
            if not connection_ids and llm_config_ids:
                connection_ids = llm_config_ids
                logger.info(f"🔄 Using llm_config_ids as connection_ids for backward compatibility")

            logger.info(f"📋 Parsed data - batch_name: {batch_name}, folder_ids: {folder_ids}, connection_ids: {connection_ids}, prompt_ids: {prompt_ids}")

            if not batch_name:
                logger.error("❌ Batch name is missing")
                return jsonify({
                    'success': False,
                    'error': 'Batch name is required'
                }), 400

            if not folder_ids:
                logger.error("❌ No folders selected")
                return jsonify({
                    'success': False,
                    'error': 'At least one folder must be selected'
                }), 400

            if not connection_ids:
                logger.error("❌ No connections selected")
                return jsonify({
                    'success': False,
                    'error': 'At least one connection must be selected'
                }), 400

            if not prompt_ids:
                logger.error("❌ No prompts selected")
                return jsonify({
                    'success': False,
                    'error': 'At least one prompt must be selected'
                }), 400

            result = staging_service.save_analysis(
                folder_ids=folder_ids,
                batch_name=batch_name,
                connection_ids=connection_ids,  # ✅ FIX: Pass selected connections
                prompt_ids=prompt_ids,  # ✅ FIX: Pass selected prompts
                meta_data=meta_data
            )

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error saving analysis: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/stage', methods=['POST'])
    def stage_analysis():
        """Stage analysis: create batch and start preprocessing"""
        try:
            data = request.get_json()
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400

            batch_name = data.get('batch_name')
            folder_ids = data.get('folder_ids', [])
            connection_ids = data.get('connection_ids', [])  # ✅ FIX: Accept selected connections
            prompt_ids = data.get('prompt_ids', [])  # ✅ FIX: Accept selected prompts
            meta_data = data.get('meta_data')

            if not batch_name:
                return jsonify({
                    'success': False,
                    'error': 'Batch name is required'
                }), 400

            if not folder_ids:
                return jsonify({
                    'success': False,
                    'error': 'At least one folder must be selected'
                }), 400

            if not connection_ids:
                return jsonify({
                    'success': False,
                    'error': 'At least one connection must be selected'
                }), 400

            if not prompt_ids:
                return jsonify({
                    'success': False,
                    'error': 'At least one prompt must be selected'
                }), 400

            result = staging_service.stage_analysis(
                folder_ids=folder_ids,
                batch_name=batch_name,
                connection_ids=connection_ids,  # ✅ FIX: Pass selected connections
                prompt_ids=prompt_ids,  # ✅ FIX: Pass selected prompts
                meta_data=meta_data
            )

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error staging analysis: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>/reprocess-staging', methods=['POST'])
    def reprocess_staging(batch_id):
        """Reprocess staging for a batch (for SAVED or FAILED_STAGING batches)"""
        try:
            # Get the batch
            from models import Batch
            from database import Session
            session = Session()

            try:
                batch = session.query(Batch).filter(Batch.id == batch_id).first()
                if not batch:
                    return jsonify({
                        'success': False,
                        'error': f'Batch {batch_id} not found'
                    }), 404

                if batch.status not in ['SAVED', 'FAILED_STAGING']:
                    return jsonify({
                        'success': False,
                        'error': f'Batch {batch_id} is not in a state that allows reprocessing staging (current: {batch.status})'
                    }), 400

                # Use the staging service to reprocess the EXISTING batch
                result = staging_service.reprocess_existing_batch_staging(
                    batch_id=batch_id,
                    folder_ids=batch.folder_ids or [],
                    batch_name=batch.batch_name,
                    meta_data=batch.meta_data
                )

                if result['success']:
                    return jsonify(result), 200
                else:
                    return jsonify(result), 400

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error reprocessing staging for batch {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>/rerun', methods=['POST'])
    def rerun_analysis(batch_id):
        """Rerun analysis for a completed batch"""
        try:
            # This would reset all LLM responses and restart analysis
            # For now, we'll use the existing run_batch functionality
            result = batch_service.run_batch(batch_id)

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error rerunning analysis for batch {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

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
            from services.batch_service import batch_service
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

    @app.route('/api/batches/<int:batch_id>/llm-responses', methods=['GET'])
    def get_batch_llm_responses(batch_id):
        """Get all LLM responses for a specific batch"""
        try:
            from database import Session
            from models import Batch, LlmResponse, Document, Prompt, Connection
            from sqlalchemy.orm import joinedload

            session = Session()
            try:
                # Verify batch exists
                batch = session.query(Batch).filter_by(id=batch_id).first()
                if not batch:
                    return jsonify({
                        'success': False,
                        'error': f'Batch {batch_id} not found'
                    }), 404

                # Get query parameters
                limit = request.args.get('limit', 100, type=int)
                offset = request.args.get('offset', 0, type=int)
                status_filter = request.args.get('status', None)

                # Build query for LLM responses in this batch
                # Note: Including connection relationship for new connections system
                query = session.query(LlmResponse).options(
                    joinedload(LlmResponse.document),
                    joinedload(LlmResponse.prompt),
                    joinedload(LlmResponse.connection)
                ).join(Document).filter(Document.batch_id == batch_id)

                # Apply status filter if provided
                if status_filter:
                    query = query.filter(LlmResponse.status == status_filter.upper())

                # Get total count for pagination
                total_count = query.count()

                # Apply pagination and ordering
                responses = query.order_by(
                    LlmResponse.timestamp.desc()
                ).offset(offset).limit(limit).all()

                # Format response data
                response_list = []
                for response in responses:
                    response_data = {
                        'id': response.id,
                        'task_id': response.task_id,
                        'status': response.status,
                        'started_processing_at': response.started_processing_at.isoformat() if response.started_processing_at else None,
                        'completed_processing_at': response.completed_processing_at.isoformat() if response.completed_processing_at else None,
                        'response_time_ms': response.response_time_ms,
                        'error_message': response.error_message,
                        'overall_score': response.overall_score,  # Include suitability score (0-100)
                        'response_json': response.response_json,  # Include full response JSON for detailed view
                        'response_text': response.response_text,  # Include response text for detailed view
                        'timestamp': response.timestamp.isoformat() if response.timestamp else None,
                        'document': {
                            'id': response.document.id,
                            'filename': response.document.filename,
                            'filepath': response.document.filepath
                        } if response.document else None,
                        'prompt': {
                            'id': response.prompt.id,
                            'description': response.prompt.description,
                            'prompt_text': response.prompt.prompt_text[:100] + '...' if response.prompt and len(response.prompt.prompt_text) > 100 else response.prompt.prompt_text if response.prompt else None
                        } if response.prompt else None,
                        'connection': {
                            'id': response.connection_id,
                            'name': response.connection.name if response.connection else None,
                            'model_name': None,  # Will be populated when schema is fixed
                            'provider_type': None  # Will be populated when schema is fixed
                        } if response.connection_id else None
                    }
                    response_list.append(response_data)

                return jsonify({
                    'success': True,
                    'batch_id': batch_id,
                    'responses': response_list,
                    'pagination': {
                        'total': total_count,
                        'limit': limit,
                        'offset': offset,
                        'has_more': offset + limit < total_count
                    }
                }), 200

            finally:
                session.close()

        except Exception as e:
            logger.error(f"Error getting batch LLM responses: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>/config-snapshot', methods=['GET'])
    def get_batch_config_snapshot(batch_id):
        """Get the configuration snapshot for a specific batch"""
        try:
            from database import Session
            from models import Batch

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

            # Temporary fix: Direct deletion without archival due to schema mismatch
            from database import Session
            from models import Batch, Document, LlmResponse

            session = Session()
            try:
                # Get the batch
                batch = session.query(Batch).filter(Batch.id == batch_id).first()
                if not batch:
                    return jsonify({
                        'success': False,
                        'error': f'Batch {batch_id} not found'
                    }), 404

                # Delete in correct order to respect foreign key constraints:
                # 1. LLM responses (reference documents)
                # 2. Docs (reference documents)
                # 3. Documents (reference batch)
                # 4. Batch

                # Get document IDs for this batch first
                document_ids = session.query(Document.id).filter(
                    Document.batch_id == batch_id
                ).all()
                document_ids = [d[0] for d in document_ids]

                # Delete LLM responses first (reference documents)
                llm_responses_deleted = 0
                if document_ids:
                    llm_responses_deleted = session.query(LlmResponse).filter(
                        LlmResponse.document_id.in_(document_ids)
                    ).delete(synchronize_session=False)

                # Delete docs (reference documents via document_id)
                docs_deleted = 0
                if document_ids:
                    from models import Doc
                    docs_deleted = session.query(Doc).filter(
                        Doc.document_id.in_(document_ids)
                    ).delete(synchronize_session=False)

                # Delete documents (reference batch)
                documents_deleted = session.query(Document).filter(
                    Document.batch_id == batch_id
                ).delete(synchronize_session=False)

                # Delete the batch
                session.delete(batch)
                session.commit()

                logger.info(f"Successfully deleted batch {batch_id}: {documents_deleted} documents, {docs_deleted} docs, {llm_responses_deleted} LLM responses")

                return jsonify({
                    'success': True,
                    'message': f'Batch {batch_id} deleted successfully',
                    'deleted_documents': documents_deleted,
                    'deleted_docs': docs_deleted,
                    'deleted_llm_responses': llm_responses_deleted
                }), 200

            except Exception as e:
                session.rollback()
                raise e
            finally:
                session.close()

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
# from api.batch_routes import register_batch_routes
# register_batch_routes(app)
