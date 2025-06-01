"""
Maintenance API Routes

Provides REST API endpoints for system maintenance operations:
- Database reset operations
- System cleanup
- Data purging
"""

import logging
import time
import uuid
import threading
import os
import subprocess
from datetime import datetime
from flask import Blueprint, request, jsonify
from sqlalchemy import text

from database import Session, get_engine
from models import Document, Snapshot, Connection, Model, LlmProvider, Batch

logger = logging.getLogger(__name__)

maintenance_bp = Blueprint('maintenance', __name__)

# Store background maintenance tasks
maintenance_tasks = {}

@maintenance_bp.route('/api/maintenance/reset', methods=['POST'])
def reset_database():
    """Reset database by clearing specified tables"""
    try:
        data = request.get_json() or {}
        
        # Generate task ID for tracking
        task_id = str(uuid.uuid4())
        
        # Initialize task tracking
        maintenance_tasks[task_id] = {
            'status': 'STARTED',
            'progress': 0,
            'total_steps': 3,
            'current_step': 0,
            'step_name': 'Initializing...',
            'deleted_counts': {},
            'error': None,
            'started_at': time.time()
        }
        
        # Start reset operation in background
        def perform_reset():
            try:
                session = Session()
                engine = get_engine()
                
                # Step 1: LLM Responses (already moved to KnowledgeDocuments database)
                maintenance_tasks[task_id].update({
                    'current_step': 1,
                    'step_name': 'LLM responses already moved to KnowledgeDocuments database',
                    'progress': 10
                })

                # Set count to 0 since table was removed
                llm_response_count = 0

                maintenance_tasks[task_id]['deleted_counts']['llm_responses'] = llm_response_count
                maintenance_tasks[task_id].update({
                    'progress': 40,
                    'step_name': f'LLM responses: {llm_response_count} (moved to KnowledgeDocuments)'
                })

                time.sleep(0.5)  # Brief pause for UI feedback
                
                # Step 2: Delete Documents
                maintenance_tasks[task_id].update({
                    'current_step': 2,
                    'step_name': 'Deleting documents...',
                    'progress': 50
                })
                
                # Count before deletion
                document_count = session.query(Document).count()
                
                # Delete all documents
                session.query(Document).delete()
                session.commit()
                
                maintenance_tasks[task_id]['deleted_counts']['documents'] = document_count
                maintenance_tasks[task_id].update({
                    'progress': 70,
                    'step_name': f'Deleted {document_count} documents'
                })
                
                time.sleep(0.5)  # Brief pause for UI feedback
                
                # Step 3: Docs (already moved to KnowledgeDocuments database)
                maintenance_tasks[task_id].update({
                    'current_step': 3,
                    'step_name': 'Docs already moved to KnowledgeDocuments database',
                    'progress': 80
                })

                # Set count to 0 since table was removed
                doc_count = 0

                maintenance_tasks[task_id]['deleted_counts']['docs'] = doc_count
                
                # Reset sequences (PostgreSQL specific)
                try:
                    with engine.connect() as conn:
                        conn.execute(text("ALTER SEQUENCE llm_responses_id_seq RESTART WITH 1"))
                        conn.execute(text("ALTER SEQUENCE documents_id_seq RESTART WITH 1"))
                        conn.execute(text("ALTER SEQUENCE docs_id_seq RESTART WITH 1"))
                        conn.commit()
                except Exception as seq_error:
                    logger.warning(f"Could not reset sequences: {seq_error}")
                
                # Final update
                maintenance_tasks[task_id].update({
                    'status': 'COMPLETED',
                    'progress': 100,
                    'step_name': 'Reset completed successfully',
                    'completed_at': time.time()
                })
                
                session.close()
                
                logger.info(f"Database reset completed. Deleted: {maintenance_tasks[task_id]['deleted_counts']}")
                
            except Exception as e:
                maintenance_tasks[task_id].update({
                    'status': 'ERROR',
                    'error': str(e),
                    'progress': 0,
                    'step_name': f'Error: {str(e)}'
                })
                logger.error(f"Database reset failed: {e}")
                if 'session' in locals():
                    session.rollback()
                    session.close()
        
        # Start background thread
        reset_thread = threading.Thread(target=perform_reset)
        reset_thread.daemon = True
        reset_thread.start()
        
        return jsonify({
            'success': True,
            'message': 'Database reset started',
            'task_id': task_id
        }), 202
        
    except Exception as e:
        logger.error(f"Error starting database reset: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@maintenance_bp.route('/api/maintenance/reset/status/<task_id>', methods=['GET'])
def get_reset_status(task_id):
    """Get the status of a reset operation"""
    try:
        if task_id not in maintenance_tasks:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404
        
        task_info = maintenance_tasks[task_id]
        
        # Calculate elapsed time
        elapsed_time = time.time() - task_info['started_at']
        
        response_data = {
            'success': True,
            'task_id': task_id,
            'status': task_info['status'],
            'progress': task_info['progress'],
            'current_step': task_info['current_step'],
            'total_steps': task_info['total_steps'],
            'step_name': task_info['step_name'],
            'deleted_counts': task_info['deleted_counts'],
            'elapsed_time': round(elapsed_time, 2)
        }
        
        if task_info['error']:
            response_data['error'] = task_info['error']
        
        if task_info['status'] == 'COMPLETED':
            response_data['completed_at'] = task_info.get('completed_at')
            response_data['total_time'] = round(task_info['completed_at'] - task_info['started_at'], 2)
        
        return jsonify(response_data), 200
        
    except Exception as e:
        logger.error(f"Error getting reset status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@maintenance_bp.route('/api/maintenance/stats', methods=['GET'])
def get_maintenance_stats():
    """Get current database statistics for maintenance overview"""
    try:
        session = Session()

        # Get counts for each table
        stats = {
            'llm_responses': 0,  # Moved to KnowledgeDocuments database
            'documents': session.query(Document).count(),
            'docs': 0,  # Moved to KnowledgeDocuments database
            'connections': session.query(Connection).count(),
            'models': session.query(Model).count(),
            'providers': session.query(LlmProvider).count(),
            'batches': session.query(Batch).count(),
            'snapshots': session.query(Snapshot).count()
        }

        session.close()

        return jsonify({
            'success': True,
            'stats': stats,
            'total_records': sum(stats.values())
        }), 200

    except Exception as e:
        logger.error(f"Error getting maintenance stats: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@maintenance_bp.route('/api/maintenance/snapshot', methods=['POST'])
def create_snapshot():
    """Create a database snapshot"""
    try:
        data = request.get_json() or {}
        snapshot_name = data.get('name', f"snapshot_{datetime.now().strftime('%Y%m%d_%H%M%S')}")
        description = data.get('description', 'Database snapshot')
        snapshot_type = data.get('type', 'quick')  # 'quick' or 'full'

        # Generate task ID for tracking
        task_id = str(uuid.uuid4())

        # Initialize task tracking
        maintenance_tasks[task_id] = {
            'status': 'STARTED',
            'progress': 0,
            'total_steps': 4,
            'current_step': 0,
            'step_name': 'Initializing snapshot...',
            'snapshot_info': {},
            'error': None,
            'started_at': time.time()
        }

        # Start snapshot operation in background
        def perform_snapshot():
            try:
                session = Session()

                # Step 1: Collect metadata
                maintenance_tasks[task_id].update({
                    'current_step': 1,
                    'step_name': 'Collecting database metadata...',
                    'progress': 10
                })

                # Get comprehensive table counts
                record_counts = {
                    'llm_responses': 0,  # Moved to KnowledgeDocuments database
                    'documents': session.query(Document).count(),
                    'docs': 0,  # Moved to KnowledgeDocuments database
                    'connections': session.query(Connection).count(),
                    'models': session.query(Model).count(),
                    'providers': session.query(LlmProvider).count(),
                    'batches': session.query(Batch).count(),
                    'snapshots': session.query(Snapshot).count()
                }

                # Get database version
                try:
                    result = session.execute(text("SELECT version()")).fetchone()
                    db_version = result[0] if result else 'Unknown'
                except:
                    db_version = 'Unknown'

                maintenance_tasks[task_id].update({
                    'progress': 25,
                    'step_name': f'Metadata collected - {sum(record_counts.values())} total records'
                })

                # Step 2: Create snapshots directory and prepare file
                maintenance_tasks[task_id].update({
                    'current_step': 2,
                    'step_name': 'Preparing snapshot file...',
                    'progress': 30
                })

                # Create snapshots directory if it doesn't exist
                snapshots_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), 'snapshots')
                os.makedirs(snapshots_dir, exist_ok=True)

                # Generate filename with timestamp
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = f"{snapshot_name}_{timestamp}.sql.gz"
                file_path = os.path.join(snapshots_dir, filename)

                maintenance_tasks[task_id].update({
                    'progress': 40,
                    'step_name': f'Snapshot file: {filename}'
                })

                # Step 3: Create database dump
                maintenance_tasks[task_id].update({
                    'current_step': 3,
                    'step_name': 'Creating database dump...',
                    'progress': 50
                })

                # PostgreSQL dump command with options based on snapshot type
                dump_cmd = [
                    '/opt/homebrew/opt/postgresql@17/bin/pg_dump',
                    '--host=studio.local',
                    '--port=5432',
                    '--username=postgres',
                    '--dbname=doc_eval',
                    '--no-password',
                    '--clean',
                    '--no-acl',
                    '--no-owner'
                ]

                # For quick snapshots, exclude the large docs table data
                if snapshot_type == 'quick':
                    dump_cmd.extend([
                        '--exclude-table-data=public.docs'
                    ])
                    maintenance_tasks[task_id].update({
                        'step_name': 'Creating quick database dump (excluding docs table data)...',
                    })
                else:
                    maintenance_tasks[task_id].update({
                        'step_name': 'Creating full database dump (including all data)...',
                    })

                # Set PGPASSWORD environment variable
                env = os.environ.copy()
                env['PGPASSWORD'] = 'prodogs03'

                # Execute pg_dump and compress with better error handling
                temp_file_path = None
                try:
                    # First, create the dump without compression to a temporary file
                    temp_file_path = file_path.replace('.gz', '.tmp')

                    with open(temp_file_path, 'w') as temp_f:
                        dump_process = subprocess.Popen(
                            dump_cmd,
                            stdout=temp_f,
                            stderr=subprocess.PIPE,
                            env=env
                        )

                        dump_output, dump_error = dump_process.communicate()

                        if dump_process.returncode != 0:
                            raise Exception(f"pg_dump failed: {dump_error.decode()}")

                    # Now compress the file
                    with open(temp_file_path, 'rb') as temp_f, open(file_path, 'wb') as compressed_f:
                        gzip_process = subprocess.Popen(
                            ['gzip', '-c'],
                            stdin=temp_f,
                            stdout=compressed_f,
                            stderr=subprocess.PIPE
                        )

                        gzip_output, gzip_error = gzip_process.communicate()

                        if gzip_process.returncode != 0:
                            raise Exception(f"gzip failed: {gzip_error.decode()}")

                    # Clean up temporary file
                    os.remove(temp_file_path)

                except Exception as e:
                    # Clean up temporary file if it exists
                    if os.path.exists(temp_file_path):
                        os.remove(temp_file_path)
                    raise e

                # Get file size
                file_size = os.path.getsize(file_path)

                maintenance_tasks[task_id].update({
                    'progress': 80,
                    'step_name': f'Database dump created ({file_size / 1024 / 1024:.1f} MB)'
                })

                # Step 4: Save snapshot record to database
                maintenance_tasks[task_id].update({
                    'current_step': 4,
                    'step_name': 'Saving snapshot record...',
                    'progress': 90
                })

                # Create snapshot record
                snapshot = Snapshot(
                    name=snapshot_name,
                    description=description,
                    file_path=file_path,
                    file_size=file_size,
                    database_name='doc_eval',
                    snapshot_type=snapshot_type,
                    compression='gzip',
                    created_by='maintenance_api',
                    tables_included=list(record_counts.keys()),
                    record_counts=record_counts,
                    database_version=db_version,
                    application_version='1.0.0',
                    status='completed'
                )

                session.add(snapshot)
                session.commit()

                # Final update
                maintenance_tasks[task_id].update({
                    'status': 'COMPLETED',
                    'progress': 100,
                    'step_name': 'Snapshot created successfully',
                    'completed_at': time.time(),
                    'snapshot_info': {
                        'id': snapshot.id,
                        'name': snapshot_name,
                        'file_path': file_path,
                        'file_size': file_size,
                        'record_counts': record_counts
                    }
                })

                session.close()

                logger.info(f"Database snapshot created: {file_path} ({file_size} bytes)")

            except Exception as e:
                maintenance_tasks[task_id].update({
                    'status': 'ERROR',
                    'error': str(e),
                    'progress': 0,
                    'step_name': f'Error: {str(e)}'
                })
                logger.error(f"Database snapshot failed: {e}")
                if 'session' in locals():
                    session.rollback()
                    session.close()

        # Start background thread
        snapshot_thread = threading.Thread(target=perform_snapshot)
        snapshot_thread.daemon = True
        snapshot_thread.start()

        return jsonify({
            'success': True,
            'message': f'{snapshot_type.title()} database snapshot started',
            'task_id': task_id,
            'snapshot_type': snapshot_type
        }), 202

    except Exception as e:
        logger.error(f"Error starting database snapshot: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@maintenance_bp.route('/api/maintenance/snapshot/status/<task_id>', methods=['GET'])
def get_snapshot_status(task_id):
    """Get the status of a snapshot operation"""
    try:
        if task_id not in maintenance_tasks:
            return jsonify({
                'success': False,
                'error': 'Task not found'
            }), 404

        task_info = maintenance_tasks[task_id]

        # Calculate elapsed time
        elapsed_time = time.time() - task_info['started_at']

        response_data = {
            'success': True,
            'task_id': task_id,
            'status': task_info['status'],
            'progress': task_info['progress'],
            'current_step': task_info['current_step'],
            'total_steps': task_info['total_steps'],
            'step_name': task_info['step_name'],
            'snapshot_info': task_info['snapshot_info'],
            'elapsed_time': round(elapsed_time, 2)
        }

        if task_info['error']:
            response_data['error'] = task_info['error']

        if task_info['status'] == 'COMPLETED':
            response_data['completed_at'] = task_info.get('completed_at')
            response_data['total_time'] = round(task_info['completed_at'] - task_info['started_at'], 2)

        return jsonify(response_data), 200

    except Exception as e:
        logger.error(f"Error getting snapshot status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@maintenance_bp.route('/api/maintenance/snapshots', methods=['GET'])
def list_snapshots():
    """List all database snapshots"""
    try:
        session = Session()

        snapshots = session.query(Snapshot).order_by(Snapshot.created_at.desc()).all()

        snapshot_list = []
        for snapshot in snapshots:
            snapshot_data = {
                'id': snapshot.id,
                'name': snapshot.name,
                'description': snapshot.description,
                'file_path': snapshot.file_path,
                'file_size': snapshot.file_size,
                'database_name': snapshot.database_name,
                'snapshot_type': snapshot.snapshot_type,
                'compression': snapshot.compression,
                'created_at': snapshot.created_at.isoformat() if snapshot.created_at else None,
                'created_by': snapshot.created_by,
                'record_counts': snapshot.record_counts,
                'database_version': snapshot.database_version,
                'status': snapshot.status,
                'notes': snapshot.notes
            }
            snapshot_list.append(snapshot_data)

        session.close()

        return jsonify({
            'success': True,
            'snapshots': snapshot_list,
            'total_snapshots': len(snapshot_list)
        }), 200

    except Exception as e:
        logger.error(f"Error listing snapshots: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@maintenance_bp.route('/api/maintenance/snapshot/<int:snapshot_id>/load', methods=['POST'])
def load_snapshot(snapshot_id):
    """Load/restore a database snapshot"""
    try:
        session = Session()

        # Get snapshot record
        snapshot = session.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
        if not snapshot:
            return jsonify({
                'success': False,
                'error': 'Snapshot not found'
            }), 404

        # Check if file exists
        if not os.path.exists(snapshot.file_path):
            return jsonify({
                'success': False,
                'error': 'Snapshot file not found'
            }), 404

        # Generate task ID for tracking
        task_id = str(uuid.uuid4())

        # Initialize task tracking
        maintenance_tasks[task_id] = {
            'status': 'STARTED',
            'progress': 0,
            'total_steps': 4,
            'current_step': 0,
            'step_name': 'Initializing snapshot restore...',
            'snapshot_info': {
                'id': snapshot.id,
                'name': snapshot.name,
                'file_path': snapshot.file_path
            },
            'error': None,
            'started_at': time.time()
        }

        session.close()

        # Start restore operation in background
        def perform_restore():
            try:
                # Step 1: Backup current database
                maintenance_tasks[task_id].update({
                    'current_step': 1,
                    'step_name': 'Creating backup of current database...',
                    'progress': 10
                })

                # Create a backup before restore
                backup_timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                backup_filename = f"pre_restore_backup_{backup_timestamp}.sql.gz"
                snapshots_dir = os.path.dirname(snapshot.file_path)
                backup_path = os.path.join(snapshots_dir, backup_filename)

                # Create backup using pg_dump
                backup_cmd = [
                    '/opt/homebrew/opt/postgresql@17/bin/pg_dump',
                    '--host=studio.local',
                    '--port=5432',
                    '--username=postgres',
                    '--dbname=doc_eval',
                    '--no-password',
                    '--clean',
                    '--no-acl',
                    '--no-owner'
                ]

                env = os.environ.copy()
                env['PGPASSWORD'] = 'prodogs03'

                with open(backup_path, 'wb') as f:
                    backup_process = subprocess.Popen(backup_cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                    gzip_process = subprocess.Popen(['gzip'], stdin=backup_process.stdout, stdout=f, stderr=subprocess.PIPE)
                    backup_process.stdout.close()

                    backup_output, backup_error = backup_process.communicate()
                    gzip_output, gzip_error = gzip_process.communicate()

                    if backup_process.returncode != 0:
                        raise Exception(f"Backup failed: {backup_error.decode()}")

                maintenance_tasks[task_id].update({
                    'progress': 30,
                    'step_name': f'Backup created: {backup_filename}'
                })

                # Step 2: Drop existing connections
                maintenance_tasks[task_id].update({
                    'current_step': 2,
                    'step_name': 'Terminating database connections...',
                    'progress': 40
                })

                # Terminate connections to the database
                terminate_cmd = [
                    '/opt/homebrew/opt/postgresql@17/bin/psql',
                    '--host=studio.local',
                    '--port=5432',
                    '--username=postgres',
                    '--dbname=postgres',
                    '--no-password',
                    '-c', "SELECT pg_terminate_backend(pid) FROM pg_stat_activity WHERE datname = 'doc_eval' AND pid <> pg_backend_pid();"
                ]

                subprocess.run(terminate_cmd, env=env, capture_output=True)

                maintenance_tasks[task_id].update({
                    'progress': 50,
                    'step_name': 'Database connections terminated'
                })

                # Step 3: Restore from snapshot
                maintenance_tasks[task_id].update({
                    'current_step': 3,
                    'step_name': 'Restoring database from snapshot...',
                    'progress': 60
                })

                # Restore using psql
                restore_cmd = [
                    '/opt/homebrew/opt/postgresql@17/bin/psql',
                    '--host=studio.local',
                    '--port=5432',
                    '--username=postgres',
                    '--dbname=doc_eval',
                    '--no-password',
                    '--quiet'
                ]

                # Decompress and restore
                with open(snapshot.file_path, 'rb') as f:
                    gunzip_process = subprocess.Popen(['gunzip', '-c'], stdin=f, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                    restore_process = subprocess.Popen(restore_cmd, stdin=gunzip_process.stdout, stdout=subprocess.PIPE, stderr=subprocess.PIPE, env=env)
                    gunzip_process.stdout.close()

                    restore_output, restore_error = restore_process.communicate()
                    gunzip_output, gunzip_error = gunzip_process.communicate()

                    if restore_process.returncode != 0:
                        raise Exception(f"Restore failed: {restore_error.decode()}")

                maintenance_tasks[task_id].update({
                    'progress': 90,
                    'step_name': 'Database restored successfully'
                })

                # Step 4: Verify restore
                maintenance_tasks[task_id].update({
                    'current_step': 4,
                    'step_name': 'Verifying restored database...',
                    'progress': 95
                })

                # Verify by checking table counts
                verify_session = Session()
                try:
                    # Simple verification - check if tables exist and have data
                    from models import Document, LlmResponse, Doc
                    doc_count = verify_session.query(Document).count()

                    maintenance_tasks[task_id].update({
                        'progress': 100,
                        'step_name': f'Restore verified - {doc_count} documents found'
                    })

                except Exception as verify_error:
                    logger.warning(f"Verification warning: {verify_error}")
                    maintenance_tasks[task_id].update({
                        'progress': 100,
                        'step_name': 'Restore completed (verification skipped)'
                    })
                finally:
                    verify_session.close()

                # Final update
                maintenance_tasks[task_id].update({
                    'status': 'COMPLETED',
                    'progress': 100,
                    'step_name': 'Database restore completed successfully',
                    'completed_at': time.time(),
                    'backup_created': backup_path
                })

                logger.info(f"Database restored from snapshot: {snapshot.file_path}")

            except Exception as e:
                maintenance_tasks[task_id].update({
                    'status': 'ERROR',
                    'error': str(e),
                    'progress': 0,
                    'step_name': f'Restore failed: {str(e)}'
                })
                logger.error(f"Database restore failed: {e}")

        # Start background thread
        restore_thread = threading.Thread(target=perform_restore)
        restore_thread.daemon = True
        restore_thread.start()

        return jsonify({
            'success': True,
            'message': 'Database restore started',
            'task_id': task_id
        }), 202

    except Exception as e:
        logger.error(f"Error starting database restore: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@maintenance_bp.route('/api/maintenance/snapshot/<int:snapshot_id>', methods=['DELETE'])
def delete_snapshot(snapshot_id):
    """Delete a snapshot file and database record"""
    try:
        session = Session()

        # Get snapshot record
        snapshot = session.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
        if not snapshot:
            session.close()
            return jsonify({
                'success': False,
                'error': 'Snapshot not found'
            }), 404

        snapshot_name = snapshot.name
        file_path = snapshot.file_path

        # Delete file if it exists
        file_deleted = False
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
                file_deleted = True
                logger.info(f"Deleted snapshot file: {file_path}")
            except Exception as e:
                logger.warning(f"Could not delete snapshot file {file_path}: {e}")

        # Delete database record
        session.delete(snapshot)
        session.commit()
        session.close()

        return jsonify({
            'success': True,
            'message': f'Snapshot "{snapshot_name}" deleted successfully',
            'file_deleted': file_deleted
        }), 200

    except Exception as e:
        logger.error(f"Error deleting snapshot: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@maintenance_bp.route('/api/maintenance/snapshot/<int:snapshot_id>', methods=['PATCH'])
def update_snapshot(snapshot_id):
    """Update snapshot name and description"""
    try:
        data = request.get_json() or {}
        session = Session()

        # Get snapshot record
        snapshot = session.query(Snapshot).filter(Snapshot.id == snapshot_id).first()
        if not snapshot:
            session.close()
            return jsonify({
                'success': False,
                'error': 'Snapshot not found'
            }), 404

        # Update fields
        if 'name' in data:
            snapshot.name = data['name']
        if 'description' in data:
            snapshot.description = data['description']
        if 'notes' in data:
            snapshot.notes = data['notes']

        session.commit()

        updated_snapshot = {
            'id': snapshot.id,
            'name': snapshot.name,
            'description': snapshot.description,
            'notes': snapshot.notes,
            'file_size': snapshot.file_size,
            'created_at': snapshot.created_at.isoformat() if snapshot.created_at else None,
            'status': snapshot.status
        }

        session.close()

        return jsonify({
            'success': True,
            'message': 'Snapshot updated successfully',
            'snapshot': updated_snapshot
        }), 200

    except Exception as e:
        logger.error(f"Error updating snapshot: {e}")
        if 'session' in locals():
            session.rollback()
            session.close()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def cleanup_old_maintenance_tasks():
    """Clean up old maintenance tasks (older than 1 hour)"""
    current_time = time.time()
    tasks_to_remove = []
    
    for task_id, task_info in maintenance_tasks.items():
        if current_time - task_info['started_at'] > 3600:  # 1 hour
            tasks_to_remove.append(task_id)
    
    for task_id in tasks_to_remove:
        del maintenance_tasks[task_id]
    
    if tasks_to_remove:
        logger.info(f"Cleaned up {len(tasks_to_remove)} old maintenance tasks")

# Register cleanup to run periodically (this would be called by a scheduler)
def register_maintenance_routes(app):
    """Register maintenance routes with the Flask app"""
    app.register_blueprint(maintenance_bp)
    logger.info("Maintenance routes registered")
