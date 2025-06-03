from flask import Blueprint, jsonify, send_file
from database import Session
from models import Document
import base64
import logging
import os

document_routes = Blueprint('document_routes', __name__)

# Store background tasks with their status
background_tasks = {}

logger = logging.getLogger(__name__)

@document_routes.route('/analyze_document_with_llm', methods=['POST'])
def analyze_document_with_llm():
    """DEPRECATED: Document analysis service moved to KnowledgeDocuments database"""
    return jsonify({
        'message': 'Document analysis service has been moved to KnowledgeDocuments database',
        'success': False,
        'deprecated': True,
        'reason': 'docs and llm_responses tables moved to separate database',
        'status': 'SERVICE_MOVED'
    }), 410  # 410 Gone - resource no longer available

@document_routes.route('/analyze_status/<task_id>', methods=['GET'])
def analyze_status(task_id):
    """DEPRECATED: Document analysis status service moved to KnowledgeDocuments database"""
    return jsonify({
        'status': 'SERVICE_MOVED',
        'totalDocuments': 0,
        'processedDocuments': 0,
        'outstandingDocuments': 0,
        'error_message': 'Document analysis service moved to KnowledgeDocuments database',
        'deprecated': True
    }), 410  # 410 Gone - resource no longer available

@document_routes.route('/api/documents/<int:document_id>', methods=['GET'])
def get_document(document_id):
    """Get document details by ID from doc_eval database"""
    try:
        session = Session()
        document = session.query(Document).filter_by(id=document_id).first()
        
        if not document:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404
        
        # Prepare document data
        # Extract file info from meta_data
        meta_data = document.meta_data or {}
        file_extension = meta_data.get('file_extension', '')
        if file_extension and file_extension.startswith('.'):
            file_extension = file_extension[1:]  # Remove leading dot
        
        # Determine MIME type
        import mimetypes
        mime_type = None
        if document.filepath:
            mime_type, _ = mimetypes.guess_type(document.filepath)
        if not mime_type and file_extension:
            mime_type, _ = mimetypes.guess_type(f'file.{file_extension}')
        
        doc_data = {
            'id': document.id,
            'filename': document.filename,
            'filepath': document.filepath,
            'doc_type': file_extension.upper() if file_extension else 'Unknown',
            'file_size': meta_data.get('file_size'),
            'mime_type': mime_type or meta_data.get('mime_type'),
            'folder_id': document.folder_id,
            'batch_id': document.batch_id,
            'valid': document.valid,
            'meta_data': meta_data,
            'created_at': document.created_at.isoformat() if document.created_at else None
        }
        
        # Try to get content if available
        try:
            # Try to read file directly if path is available
            if document.filepath:
                try:
                    with open(document.filepath, 'r', encoding='utf-8') as f:
                        doc_data['content'] = f.read()
                except UnicodeDecodeError:
                    # Try reading as binary and encode to base64
                    try:
                        with open(document.filepath, 'rb') as f:
                            content_bytes = f.read()
                            doc_data['base64_content'] = base64.b64encode(content_bytes).decode('utf-8')
                            doc_data['content'] = None
                            doc_data['is_binary'] = True
                    except Exception as e:
                        doc_data['content'] = None
                        doc_data['error'] = f'Unable to read binary file: {str(e)}'
                except FileNotFoundError:
                    doc_data['content'] = None
                    doc_data['error'] = 'File not found at the specified path'
                except Exception as e:
                    doc_data['content'] = None
                    doc_data['error'] = f'Unable to read file: {str(e)}'
            else:
                doc_data['content'] = None
                doc_data['error'] = 'No file path available'
        except Exception as e:
            logger.error(f"Error getting document content: {e}")
            doc_data['content'] = None
            doc_data['error'] = str(e)
        
        session.close()
        
        return jsonify({
            'success': True,
            'document': doc_data
        })
        
    except Exception as e:
        logger.error(f"Error getting document {document_id}: {e}")
        if 'session' in locals():
            session.close()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@document_routes.route('/api/documents/<int:document_id>/download', methods=['GET'])
def download_document(document_id):
    """Download document file from doc_eval database"""
    try:
        session = Session()
        document = session.query(Document).filter_by(id=document_id).first()
        
        if not document:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404
        
        # Check if file exists
        if not document.filepath or not os.path.exists(document.filepath):
            return jsonify({
                'success': False,
                'error': 'Document file not found'
            }), 404
        
        # Determine MIME type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(document.filepath)
        if not mime_type:
            # Try from meta_data
            meta_data = document.meta_data or {}
            mime_type = meta_data.get('mime_type', 'application/octet-stream')
        
        session.close()
        
        # Send file for download
        return send_file(
            document.filepath,
            as_attachment=True,
            download_name=document.filename or 'document',
            mimetype=mime_type or 'application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error downloading document {document_id}: {e}")
        if 'session' in locals():
            session.close()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@document_routes.route('/api/documents/<int:document_id>/view', methods=['GET'])
def view_document(document_id):
    """View document file inline (for PDFs, images, etc.)"""
    try:
        session = Session()
        document = session.query(Document).filter_by(id=document_id).first()
        
        if not document:
            return jsonify({
                'success': False,
                'error': 'Document not found'
            }), 404
        
        # Check if file exists
        if not document.filepath or not os.path.exists(document.filepath):
            return jsonify({
                'success': False,
                'error': 'Document file not found'
            }), 404
        
        # Determine MIME type
        import mimetypes
        mime_type, _ = mimetypes.guess_type(document.filepath)
        if not mime_type:
            # Try from meta_data
            meta_data = document.meta_data or {}
            mime_type = meta_data.get('mime_type', 'application/octet-stream')
        
        session.close()
        
        # For viewing, don't force download
        return send_file(
            document.filepath,
            as_attachment=False,  # This allows inline viewing
            download_name=document.filename or 'document',
            mimetype=mime_type or 'application/octet-stream'
        )
        
    except Exception as e:
        logger.error(f"Error downloading document {document_id}: {e}")
        if 'session' in locals():
            session.close()
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def register_document_routes(app):
    """Register document routes with the Flask app"""
    app.register_blueprint(document_routes)

    # Make background_tasks available globally
    app.config['BACKGROUND_TASKS'] = background_tasks

    return app