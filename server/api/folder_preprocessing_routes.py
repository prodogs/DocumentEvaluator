"""
Folder Preprocessing API Routes

New endpoints for the folder preprocessing workflow:
- POST /api/folders/preprocess - Start folder preprocessing
- GET /api/folders/{id}/status - Get preprocessing status
- GET /api/folders/ready - Get folders ready for batch creation
"""

from flask import Blueprint, request, jsonify
import logging
import os
from services.folder_preprocessing_service import FolderPreprocessingService
from database import Session
from models import Folder, Document, Doc
from sqlalchemy import func, case

folder_preprocessing_bp = Blueprint('folder_preprocessing', __name__)
logger = logging.getLogger(__name__)

@folder_preprocessing_bp.route('/api/folders/preprocess', methods=['POST'])
def preprocess_folder():
    """
    Start folder preprocessing workflow

    Expected JSON:
    {
        "folder_path": "/path/to/folder",
        "folder_name": "My Folder Name"
    }
    """
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'JSON data required'}), 400

        folder_path = data.get('folder_path')
        folder_name = data.get('folder_name')

        if not folder_path:
            return jsonify({'error': 'folder_path is required'}), 400

        if not folder_name:
            return jsonify({'error': 'folder_name is required'}), 400

        # Validate folder exists
        if not os.path.exists(folder_path):
            return jsonify({'error': f'Folder does not exist: {folder_path}'}), 400

        if not os.path.isdir(folder_path):
            return jsonify({'error': f'Path is not a directory: {folder_path}'}), 400

        # Start preprocessing asynchronously
        import threading
        import uuid

        # Generate task ID for tracking
        task_id = str(uuid.uuid4())

        # Initialize task status in global storage
        from flask import current_app
        if not hasattr(current_app, 'preprocessing_tasks'):
            current_app.preprocessing_tasks = {}

        current_app.preprocessing_tasks[task_id] = {
            'status': 'STARTING',
            'folder_path': folder_path,
            'folder_name': folder_name,
            'progress': 0,
            'total_files': 0,
            'processed_files': 0,
            'valid_files': 0,
            'invalid_files': 0,
            'error': None,
            'folder_id': None
        }

        # Start preprocessing in background thread
        def background_preprocessing():
            # Get the current Flask app instance
            app = current_app._get_current_object()

            # Run within application context
            with app.app_context():
                try:
                    preprocessing_service = FolderPreprocessingService()
                    results = preprocessing_service.preprocess_folder_async(folder_path, folder_name, task_id, app)

                    # Update final status
                    app.preprocessing_tasks[task_id].update({
                        'status': 'COMPLETED',
                        'progress': 100,
                        'results': results
                    })

                except Exception as e:
                    logger.error(f"Background preprocessing failed: {e}")
                    app.preprocessing_tasks[task_id].update({
                        'status': 'ERROR',
                        'error': str(e)
                    })

        thread = threading.Thread(target=background_preprocessing)
        thread.daemon = True
        thread.start()

        return jsonify({
            'message': 'Folder preprocessing started',
            'task_id': task_id
        }), 202

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error preprocessing folder: {e}")
        return jsonify({'error': f'Preprocessing failed: {str(e)}'}), 500

@folder_preprocessing_bp.route('/api/folders/task/<task_id>/status', methods=['GET'])
def get_task_status(task_id):
    """Get preprocessing task status"""
    try:
        from flask import current_app

        if not hasattr(current_app, 'preprocessing_tasks'):
            return jsonify({'error': 'Task not found'}), 404

        task = current_app.preprocessing_tasks.get(task_id)
        if not task:
            return jsonify({'error': 'Task not found'}), 404

        return jsonify(task), 200

    except Exception as e:
        logger.error(f"Error getting task status: {e}")
        return jsonify({'error': str(e)}), 500

@folder_preprocessing_bp.route('/api/folders/<int:folder_id>/status', methods=['GET'])
def get_folder_status(folder_id):
    """Get folder preprocessing status and statistics"""
    try:
        preprocessing_service = FolderPreprocessingService()
        status = preprocessing_service.get_folder_status(folder_id)

        if not status:
            return jsonify({'error': 'Folder not found'}), 404

        return jsonify({
            'folder_status': status
        }), 200

    except Exception as e:
        logger.error(f"Error getting folder status: {e}")
        return jsonify({'error': str(e)}), 500

@folder_preprocessing_bp.route('/api/folders/<int:folder_id>/failed-files', methods=['GET'])
def get_failed_files(folder_id):
    """Get all failed files for a folder with their failure reasons"""
    session = Session()
    try:
        # Query failed documents with their metadata
        failed_documents = session.query(Document).filter(
            Document.folder_id == folder_id,
            Document.valid == 'N'
        ).all()

        failed_files = []
        for doc in failed_documents:
            meta_data = doc.meta_data or {}
            failed_files.append({
                'id': doc.id,
                'filename': doc.filename,
                'filepath': doc.filepath,
                'relative_path': meta_data.get('relative_path', ''),
                'validation_reason': meta_data.get('validation_reason', 'Unknown error'),
                'file_size': meta_data.get('file_size', 0),
                'file_extension': meta_data.get('file_extension', ''),
                'created_at': doc.created_at.isoformat() if doc.created_at else None
            })

        return jsonify({
            'failed_files': failed_files,
            'count': len(failed_files),
            'folder_id': folder_id
        }), 200

    except Exception as e:
        logger.error(f"Error getting failed files for folder {folder_id}: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@folder_preprocessing_bp.route('/api/folders/ready', methods=['GET'])
def get_ready_folders():
    """Get all folders that are ready for batch creation"""
    session = Session()
    try:
        # Query folders with aggregated document statistics
        results = session.query(
            Folder.id,
            Folder.folder_name,
            Folder.folder_path,
            Folder.status,
            func.count(Document.id).label('total_documents'),
            func.sum(case((Document.valid == 'Y', 1), else_=0)).label('valid_documents'),
            func.sum(case((Document.valid == 'N', 1), else_=0)).label('invalid_documents'),
            func.coalesce(func.sum(Doc.file_size), 0).label('total_size'),
            func.coalesce(func.sum(case((Document.valid == 'Y', Doc.file_size), else_=0)), 0).label('ready_files_size'),
            Folder.active
        ).outerjoin(Document, Folder.id == Document.folder_id)\
         .outerjoin(Doc, Document.id == Doc.document_id)\
         .filter(Folder.status == 'READY', Folder.active == 1)\
         .group_by(Folder.id, Folder.folder_name, Folder.folder_path, Folder.status, Folder.active)\
         .order_by(Folder.folder_name)\
         .all()

        folders = []
        for row in results:
            folders.append({
                'id': row[0],
                'folder_name': row[1],
                'folder_path': row[2],
                'status': row[3],
                'total_documents': row[4],
                'valid_documents': row[5],
                'invalid_documents': row[6],
                'total_size': row[7],
                'ready_files_size': row[8],
                'active': bool(row[9])
            })

        return jsonify({
            'folders': folders,
            'count': len(folders)
        }), 200

    except Exception as e:
        logger.error(f"Error getting ready folders: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@folder_preprocessing_bp.route('/api/folders/<int:folder_id>/documents', methods=['GET'])
def get_folder_documents(folder_id):
    """Get all documents in a folder with their validation status"""
    session = Session()
    try:
        # Get folder info
        folder = session.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            return jsonify({'error': 'Folder not found'}), 404

        # Get documents with their doc info
        documents_query = session.query(
            Document.id,
            Document.filepath,
            Document.filename,
            Document.valid,
            Doc.doc_type,
            Doc.file_size
        ).outerjoin(Doc, Document.id == Doc.document_id)\
         .filter(Document.folder_id == folder_id)\
         .order_by(Document.filepath)\
         .all()

        documents = []
        for row in documents_query:
            # Calculate relative path
            relative_path = row[1]
            if folder.folder_path and row[1].startswith(folder.folder_path):
                relative_path = row[1][len(folder.folder_path):].lstrip('/')

            documents.append({
                'id': row[0],
                'file_path': row[1],
                'filename': row[2],
                'relative_path': relative_path,
                'valid': row[3] == 'Y',
                'doc_type': row[4],
                'file_size': row[5] or 0
            })

        return jsonify({
            'folder': {
                'id': folder_id,
                'folder_name': folder.folder_name,
                'folder_path': folder.folder_path,
                'status': folder.status
            },
            'documents': documents,
            'total_documents': len(documents),
            'valid_documents': len([d for d in documents if d['valid']]),
            'invalid_documents': len([d for d in documents if not d['valid']])
        }), 200

    except Exception as e:
        logger.error(f"Error getting folder documents: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        session.close()

@folder_preprocessing_bp.route('/api/folders/<int:folder_id>/reprocess', methods=['POST'])
def reprocess_folder(folder_id):
    """Reprocess an existing folder (clear existing documents and reprocess)"""
    session = Session()
    try:
        # Get folder info
        folder = session.query(Folder).filter(Folder.id == folder_id).first()
        if not folder:
            return jsonify({'error': 'Folder not found'}), 404

        folder_name = folder.folder_name
        folder_path = folder.folder_path

        # Delete existing docs for documents in this folder
        docs_to_delete = session.query(Doc).join(Document).filter(Document.folder_id == folder_id)
        docs_to_delete.delete(synchronize_session=False)

        # Delete existing documents for this folder
        documents_to_delete = session.query(Document).filter(Document.folder_id == folder_id)
        documents_to_delete.delete(synchronize_session=False)

        session.commit()
        session.close()

        # Start preprocessing
        preprocessing_service = FolderPreprocessingService()
        results = preprocessing_service.preprocess_folder(folder_path, folder_name)

        return jsonify({
            'message': 'Folder reprocessing completed successfully',
            'results': results
        }), 200

    except Exception as e:
        if session:
            session.rollback()
            session.close()
        logger.error(f"Error reprocessing folder: {e}")
        return jsonify({'error': f'Reprocessing failed: {str(e)}'}), 500
