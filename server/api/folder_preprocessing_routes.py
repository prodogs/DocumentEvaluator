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
from database import get_db_connection

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

        # Start preprocessing
        preprocessing_service = FolderPreprocessingService()
        results = preprocessing_service.preprocess_folder(folder_path, folder_name)

        return jsonify({
            'message': 'Folder preprocessing completed successfully',
            'results': results
        }), 200

    except ValueError as e:
        return jsonify({'error': str(e)}), 400
    except Exception as e:
        logger.error(f"Error preprocessing folder: {e}")
        return jsonify({'error': f'Preprocessing failed: {str(e)}'}), 500

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

@folder_preprocessing_bp.route('/api/folders/ready', methods=['GET'])
def get_ready_folders():
    """Get all folders that are ready for batch creation"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        cursor.execute("""
            SELECT f.id, f.folder_name, f.folder_path, f.status,
                   COUNT(d.id) as total_documents,
                   COUNT(CASE WHEN d.valid = 'Y' THEN 1 END) as valid_documents,
                   COUNT(CASE WHEN d.valid = 'N' THEN 1 END) as invalid_documents,
                   COALESCE(SUM(docs.file_size), 0) as total_size,
                   f.active
            FROM folders f
            LEFT JOIN documents d ON f.id = d.folder_id
            LEFT JOIN docs ON d.id = docs.document_id
            WHERE f.status = 'READY' AND f.active = 1
            GROUP BY f.id, f.folder_name, f.folder_path, f.status, f.active
            ORDER BY f.folder_name
        """)

        folders = []
        for row in cursor.fetchall():
            folders.append({
                'id': row[0],
                'folder_name': row[1],
                'folder_path': row[2],
                'status': row[3],
                'total_documents': row[4],
                'valid_documents': row[5],
                'invalid_documents': row[6],
                'total_size': row[7],
                'active': bool(row[8])
            })

        return jsonify({
            'folders': folders,
            'count': len(folders)
        }), 200

    except Exception as e:
        logger.error(f"Error getting ready folders: {e}")
        return jsonify({'error': str(e)}), 500
    finally:
        if conn:
            conn.close()

@folder_preprocessing_bp.route('/api/folders/<int:folder_id>/documents', methods=['GET'])
def get_folder_documents(folder_id):
    """Get all documents in a folder with their validation status"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get folder info
        cursor.execute("""
            SELECT folder_name, folder_path, status
            FROM folders
            WHERE id = %s
        """, (folder_id,))

        folder_info = cursor.fetchone()
        if not folder_info:
            return jsonify({'error': 'Folder not found'}), 404

        # Get documents
        cursor.execute("""
            SELECT d.id, d.filepath, d.filename, d.valid,
                   docs.doc_type, docs.file_size,
                   SUBSTRING(d.filepath FROM LENGTH(%s) + 2) as relative_path
            FROM documents d
            LEFT JOIN docs ON d.id = docs.document_id
            WHERE d.folder_id = %s
            ORDER BY d.filepath
        """, (folder_info[1], folder_id))

        documents = []
        for row in cursor.fetchall():
            documents.append({
                'id': row[0],
                'file_path': row[1],
                'filename': row[2],
                'relative_path': row[6],
                'valid': row[3] == 'Y',
                'doc_type': row[4],
                'file_size': row[5] or 0
            })

        return jsonify({
            'folder': {
                'id': folder_id,
                'folder_name': folder_info[0],
                'folder_path': folder_info[1],
                'status': folder_info[2]
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
        if conn:
            conn.close()

@folder_preprocessing_bp.route('/api/folders/<int:folder_id>/reprocess', methods=['POST'])
def reprocess_folder(folder_id):
    """Reprocess an existing folder (clear existing documents and reprocess)"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Get folder info
        cursor.execute("""
            SELECT folder_name, folder_path
            FROM folders
            WHERE id = %s
        """, (folder_id,))

        folder_info = cursor.fetchone()
        if not folder_info:
            return jsonify({'error': 'Folder not found'}), 404

        folder_name, folder_path = folder_info

        # Delete existing documents and docs for this folder
        cursor.execute("""
            DELETE FROM docs
            WHERE document_id IN (
                SELECT id FROM documents WHERE folder_id = %s
            )
        """, (folder_id,))

        cursor.execute("""
            DELETE FROM documents
            WHERE folder_id = %s
        """, (folder_id,))

        conn.commit()
        conn.close()

        # Start preprocessing
        preprocessing_service = FolderPreprocessingService()
        results = preprocessing_service.preprocess_folder(folder_path, folder_name)

        return jsonify({
            'message': 'Folder reprocessing completed successfully',
            'results': results
        }), 200

    except Exception as e:
        if conn:
            conn.rollback()
            conn.close()
        logger.error(f"Error reprocessing folder: {e}")
        return jsonify({'error': f'Reprocessing failed: {str(e)}'}), 500
