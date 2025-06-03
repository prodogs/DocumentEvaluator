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
# Staging functionality now integrated into BatchService

logger = logging.getLogger(__name__)


def _format_connection_for_response(response):
    """
    Format connection information for API response using stored connection_details or fallback to current connection.

    Args:
        response: LlmResponse object

    Returns:
        Dictionary with connection information or None
    """
    from utils.connection_utils import format_connection_for_api_response

    # Use stored connection details if available, with fallback to current connection
    return format_connection_for_api_response(
        connection_details=response.connection_details,
        fallback_connection=response.connection if hasattr(response, 'connection') else None
    )


def register_batch_routes(app):
    """Register batch management routes with the Flask app"""

    @app.route('/api/batches/save', methods=['POST'])
    def save_analysis():
        """Save analysis configuration as a batch with SAVED status"""
        try:
            data = request.get_json(force=True, silent=True)
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

            # Use unified batch service to save batch
            result = batch_service.save_batch(
                folder_ids=folder_ids,
                connection_ids=connection_ids,
                prompt_ids=prompt_ids,
                batch_name=batch_name,
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
            data = request.get_json(force=True, silent=True)
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

            # Use unified batch service to stage batch
            result = batch_service.stage_batch(
                folder_ids=folder_ids,
                connection_ids=connection_ids,
                prompt_ids=prompt_ids,
                batch_name=batch_name,
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

    @app.route('/api/batches/<int:batch_id>/stage', methods=['POST'])
    def stage_saved_batch(batch_id):
        """Stage a saved batch - prepare documents for processing"""
        try:
            logger.info(f"Stage batch requested for batch {batch_id}")

            # Use centralized state management with 'stage' action
            result = batch_service.request_state_change(batch_id, 'stage', {})

            if result['success']:
                logger.info(f"Batch {batch_id} staging completed successfully")
                return jsonify(result), 200
            else:
                logger.warning(f"Batch {batch_id} staging failed: {result.get('error', 'Unknown error')}")
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error staging batch {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
                'batch_id': batch_id
            }), 500

    @app.route('/api/batches/<int:batch_id>/reprocess-staging', methods=['POST'])
    def reprocess_staging(batch_id):
        """Reprocess staging for a batch - prepare documents and update batch status"""
        try:
            logger.info(f"Reprocess staging requested for batch {batch_id}")

            # Use centralized state management
            result = batch_service.request_state_change(batch_id, 'restage', {})

            if result['success']:
                logger.info(f"Batch {batch_id} staging completed successfully")
                return jsonify(result), 200
            else:
                logger.warning(f"Batch {batch_id} staging failed: {result.get('error', 'Unknown error')}")
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error in reprocess staging for batch {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
                'batch_id': batch_id
            }), 500

    @app.route('/api/batches/<int:batch_id>/rerun', methods=['POST'])
    def rerun_analysis(batch_id):
        """Rerun analysis for a completed batch"""
        try:
            # Use centralized state management
            result = batch_service.request_state_change(batch_id, 'rerun', {})

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
            data = request.get_json(force=True, silent=True)
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
        """Get LLM responses for batch from KnowledgeDocuments database using batch_id"""
        try:
            import psycopg2
            import json
            from database import Session
            from models import Document
            
            # Get limit and offset for pagination
            limit = int(request.args.get('limit', 50))
            offset = int(request.args.get('offset', 0))
            
            # Connect to KnowledgeDocuments database
            kb_conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            kb_cursor = kb_conn.cursor()
            
            # Query LLM responses directly by batch_id (much simpler!)
            kb_cursor.execute("""
                SELECT 
                    lr.id, lr.document_id, lr.prompt_id, lr.connection_id, lr.connection_details,
                    lr.task_id, lr.status, lr.started_processing_at, lr.completed_processing_at,
                    lr.response_json, lr.response_text, lr.response_time_ms, lr.error_message,
                    lr.overall_score, lr.input_tokens, lr.output_tokens, lr.time_taken_seconds,
                    lr.tokens_per_second, lr.timestamp, lr.created_at, lr.batch_id,
                    d.document_id as kb_document_id
                FROM llm_responses lr
                JOIN docs d ON lr.document_id = d.id
                WHERE lr.batch_id = %s
                ORDER BY lr.created_at DESC
                LIMIT %s OFFSET %s
            """, (batch_id, limit, offset))
                
            llm_responses = kb_cursor.fetchall()
            
            # Get total count for pagination
            kb_cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE batch_id = %s", (batch_id,))
            total_count = kb_cursor.fetchone()[0]
            
            kb_cursor.close()
            kb_conn.close()
            
            # Get prompt, connection, and document data from doc_eval database
            session = Session()
            try:
                from models import Prompt, Connection, Document
                
                # Get all unique prompt, connection, and document IDs from responses
                prompt_ids = set()
                connection_ids = set()
                doc_eval_document_ids = set()
                
                for response in llm_responses:
                    if response[2]:  # prompt_id
                        prompt_ids.add(response[2])
                    if response[3]:  # connection_id
                        connection_ids.add(response[3])
                    
                    # Extract doc_eval document_id from kb_document_id pattern
                    kb_document_id = response[19]  # kb_document_id
                    if kb_document_id:
                        import re
                        # Ensure kb_document_id is a string
                        kb_doc_id_str = str(kb_document_id) if kb_document_id else ""
                        match = re.match(r'batch_\d+_doc_(\d+)', kb_doc_id_str)
                        if match:
                            doc_eval_document_ids.add(int(match.group(1)))
                
                from models import Model
                
                # Fetch prompts, connections, and documents
                prompts = {p.id: p for p in session.query(Prompt).filter(Prompt.id.in_(prompt_ids)).all()} if prompt_ids else {}
                connections = {c.id: c for c in session.query(Connection).filter(Connection.id.in_(connection_ids)).all()} if connection_ids else {}
                documents = {d.id: d for d in session.query(Document).filter(Document.id.in_(doc_eval_document_ids)).all()} if doc_eval_document_ids else {}
                
                # Fetch models for connections that have model_id
                model_ids = {c.model_id for c in connections.values() if c.model_id}
                models = {m.id: m for m in session.query(Model).filter(Model.id.in_(model_ids)).all()} if model_ids else {}
                
                # Format responses for API
                formatted_responses = []
                for response in llm_responses:
                    (id, document_id, prompt_id, connection_id, connection_details,
                     task_id, status, started_processing_at, completed_processing_at,
                     response_json, response_text, response_time_ms, error_message,
                     overall_score, input_tokens, output_tokens, time_taken_seconds,
                     tokens_per_second, timestamp, created_at, batch_id_field,
                     kb_document_id) = response
                    
                    # Parse connection details
                    connection_details_parsed = None
                    if connection_details:
                        try:
                            if isinstance(connection_details, str):
                                connection_details_parsed = json.loads(connection_details)
                            else:
                                connection_details_parsed = connection_details
                        except:
                            connection_details_parsed = connection_details
                    
                    # Extract document_id from kb_document_id pattern (batch_{batch_id}_doc_{doc_id})
                    doc_eval_document_id = None
                    if kb_document_id:
                        import re
                        # Ensure kb_document_id is a string
                        kb_doc_id_str = str(kb_document_id) if kb_document_id else ""
                        match = re.match(r'batch_\d+_doc_(\d+)', kb_doc_id_str)
                        if match:
                            doc_eval_document_id = int(match.group(1))
                    
                    # Get prompt, connection, and document objects
                    prompt_obj = prompts.get(prompt_id) if prompt_id else None
                    connection_obj = connections.get(connection_id) if connection_id else None
                    
                    # Fetch document directly from database
                    document_obj = None
                    if doc_eval_document_id:
                        document_obj = session.query(Document).filter_by(id=doc_eval_document_id).first()
                    
                    # Get model name for connection
                    model_name = None
                    if connection_obj and connection_obj.model_id:
                        model_obj = models.get(connection_obj.model_id)
                        model_name = model_obj.display_name if model_obj else connection_details_parsed.get('model_name') if connection_details_parsed else None
                    elif connection_details_parsed:
                        model_name = connection_details_parsed.get('model_name')
                    
                    formatted_response = {
                        'id': id,
                        'kb_document_id': document_id,
                        'doc_eval_document_id': doc_eval_document_id,
                        'filename': document_obj.filename if document_obj else 'Unknown document',
                        'filepath': document_obj.filepath if document_obj else 'Unknown path',
                        'document': {
                            'filename': document_obj.filename if document_obj else 'Unknown document',
                            'filepath': document_obj.filepath if document_obj else 'Unknown path',
                            'doc_type': document_obj.doc_type if document_obj else 'Unknown',
                            'file_size': document_obj.file_size if document_obj else None,
                            'id': document_obj.id if document_obj else None
                        },
                        'prompt_id': prompt_id,
                        'prompt': {
                            'id': prompt_obj.id if prompt_obj else prompt_id,
                            'description': prompt_obj.description if prompt_obj else 'Unknown prompt',
                            'prompt_text': prompt_obj.prompt_text if prompt_obj else None
                        } if prompt_obj or prompt_id else None,
                        'connection_id': connection_id,
                        'connection_details': connection_details_parsed,
                        'connection': {
                            'id': connection_obj.id if connection_obj else connection_id,
                            'name': connection_obj.name if connection_obj else connection_details_parsed.get('name', 'Unknown connection'),
                            'model_name': model_name,
                            'provider_type': connection_details_parsed.get('provider_type') if connection_details_parsed else 'Unknown'
                        } if connection_obj or connection_details_parsed else None,
                        'task_id': task_id,
                        'status': status,
                        'started_processing_at': started_processing_at.isoformat() if started_processing_at and hasattr(started_processing_at, 'isoformat') else str(started_processing_at) if started_processing_at else None,
                        'completed_processing_at': completed_processing_at.isoformat() if completed_processing_at and hasattr(completed_processing_at, 'isoformat') else str(completed_processing_at) if completed_processing_at else None,
                        'response_json': response_json,
                        'response_text': response_text,
                        'response_time_ms': response_time_ms,
                        'error_message': error_message,
                        'overall_score': overall_score,
                        'input_tokens': input_tokens,
                        'output_tokens': output_tokens,
                        'time_taken_seconds': time_taken_seconds,
                        'tokens_per_second': tokens_per_second,
                        'timestamp': timestamp.isoformat() if timestamp and hasattr(timestamp, 'isoformat') else str(timestamp) if timestamp else None,
                        'created_at': created_at.isoformat() if created_at and hasattr(created_at, 'isoformat') else str(created_at) if created_at else None,
                        'batch_id': batch_id_field
                    }
                    formatted_responses.append(formatted_response)
                
                # Calculate pagination info
                has_more = (offset + limit) < total_count
                
                return jsonify({
                    'success': True,
                    'responses': formatted_responses,
                    'pagination': {
                        'total': total_count,
                        'limit': limit,
                        'offset': offset,
                        'has_more': has_more
                    },
                    'batch_id': batch_id
                })
            finally:
                session.close()
                
        except Exception as e:
            logger.error(f"Error getting batch LLM responses for batch {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e),
                'batch_id': batch_id
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
            # Use centralized state management
            result = batch_service.request_state_change(batch_id, 'pause', {})

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
            # Use centralized state management
            result = batch_service.request_state_change(batch_id, 'resume', {})

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

    @app.route('/api/batches/<int:batch_id>/reset-to-prestage', methods=['POST'])
    def reset_batch_to_prestage(batch_id):
        """Reset a stuck batch back to prestage (SAVED) state"""
        try:
            # Use centralized state management
            result = batch_service.request_state_change(batch_id, 'reset', {})

            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400

        except Exception as e:
            logger.error(f"Error resetting batch {batch_id} to prestage: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>', methods=['DELETE'])
    def delete_batch(batch_id):
        """Archive and delete a batch with all associated data"""
        try:
            data = request.get_json(force=True, silent=True) or {}
            archived_by = data.get('archived_by', 'User')
            archive_reason = data.get('archive_reason', 'Manual deletion via UI')

            # Direct deletion without archival - LLM responses moved to KnowledgeDocuments database
            from database import Session
            from models import Batch, Document

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
                # 1. Docs (reference documents)
                # 2. Documents (reference batch)
                # 3. Batch
                # Note: LLM responses moved to KnowledgeDocuments database

                # Get document IDs for this batch first
                document_ids = session.query(Document.id).filter(
                    Document.batch_id == batch_id
                ).all()
                document_ids = [d[0] for d in document_ids]

                # LLM responses deletion skipped - moved to KnowledgeDocuments database
                llm_responses_deleted = 0  # LLM responses moved to KnowledgeDocuments database

                # Note: docs table moved to KnowledgeDocuments database - no cleanup needed
                docs_deleted = 0  # docs table moved to KnowledgeDocuments database

                # Delete documents (reference batch)
                documents_deleted = session.query(Document).filter(
                    Document.batch_id == batch_id
                ).delete(synchronize_session=False)

                # Delete the batch
                session.delete(batch)
                session.commit()

                logger.info(f"Successfully deleted batch {batch_id}: {documents_deleted} documents, {docs_deleted} docs (LLM responses in KnowledgeDocuments database)")

                return jsonify({
                    'success': True,
                    'message': f'Batch {batch_id} deleted successfully',
                    'deleted_documents': documents_deleted,
                    'deleted_docs': docs_deleted,
                    'deleted_llm_responses': llm_responses_deleted,
                    'note': 'LLM responses stored in KnowledgeDocuments database'
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


    @app.route('/api/batches/<int:batch_id>/check-completion', methods=['POST'])
    def check_batch_completion(batch_id):
        """Manually trigger batch completion check for a specific batch"""
        try:
            logger.info(f"Manual batch completion check requested for batch {batch_id}")
            
            # Call the completion check method directly
            result = batch_service.check_and_update_batch_completion(batch_id)
            
            if result:
                return jsonify({
                    'success': True,
                    'message': f'Batch {batch_id} completion check completed - batch is now COMPLETED',
                    'batch_completed': True
                }), 200
            else:
                return jsonify({
                    'success': True,
                    'message': f'Batch {batch_id} completion check completed - batch is still processing',
                    'batch_completed': False
                }), 200
                
        except Exception as e:
            logger.error(f"Error checking batch completion for {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    @app.route('/api/batches/<int:batch_id>/action', methods=['POST'])
    def batch_action(batch_id):
        """Unified endpoint for all batch state change requests"""
        try:
            data = request.get_json(force=True, silent=True)
            if not data:
                return jsonify({
                    'success': False,
                    'error': 'No data provided'
                }), 400
                
            action = data.get('action')
            context = data.get('context', {})
            
            if not action:
                return jsonify({
                    'success': False,
                    'error': 'Action is required'
                }), 400
                
            # Log the action request
            logger.info(f"Batch action requested: batch_id={batch_id}, action={action}, context={context}")
            
            # Use centralized state management
            result = batch_service.request_state_change(batch_id, action, context)
            
            if result['success']:
                return jsonify(result), 200
            else:
                return jsonify(result), 400
                
        except Exception as e:
            logger.error(f"Error performing batch action {action} on batch {batch_id}: {e}", exc_info=True)
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

    logger.info("Batch management routes registered")

# Example usage in app_launcher.py:
# from api.batch_routes import register_batch_routes
# register_batch_routes(app)
