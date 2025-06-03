"""
Document Type API Routes
"""

from flask import Blueprint, request, jsonify
from services.document_type_service import document_type_service
import logging

logger = logging.getLogger(__name__)

document_type_bp = Blueprint('document_types', __name__)

@document_type_bp.route('/api/document-types', methods=['GET'])
def get_document_types():
    """Get all document types"""
    try:
        document_types = document_type_service.get_all_document_types()
        
        return jsonify({
            'success': True,
            'document_types': document_types,
            'total': len(document_types)
        })
        
    except Exception as e:
        logger.error(f"Error getting document types: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@document_type_bp.route('/api/document-types/valid', methods=['GET'])
def get_valid_document_types():
    """Get only valid document types"""
    try:
        extensions = document_type_service.get_valid_extensions()
        mime_types = document_type_service.get_mime_type_mapping()
        supported_list = document_type_service.get_supported_extensions_list()
        
        return jsonify({
            'success': True,
            'valid_extensions': extensions,
            'mime_types': mime_types,
            'supported_description': supported_list,
            'total': len(extensions)
        })
        
    except Exception as e:
        logger.error(f"Error getting valid document types: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@document_type_bp.route('/api/document-types/validate', methods=['POST'])
def validate_files():
    """Validate a list of filenames"""
    try:
        data = request.get_json()
        filenames = data.get('filenames', [])
        
        if not isinstance(filenames, list):
            return jsonify({
                'success': False,
                'error': 'filenames must be a list'
            }), 400
        
        valid_files, invalid_files = document_type_service.validate_file_batch(filenames)
        
        # Get detailed info for invalid files
        invalid_details = []
        for filename in invalid_files:
            info = document_type_service.get_file_type_info(filename)
            invalid_details.append({
                'filename': filename,
                'extension': info['extension'],
                'reason': info['description']
            })
        
        return jsonify({
            'success': True,
            'valid_files': valid_files,
            'invalid_files': invalid_files,
            'invalid_details': invalid_details,
            'summary': {
                'total': len(filenames),
                'valid': len(valid_files),
                'invalid': len(invalid_files)
            }
        })
        
    except Exception as e:
        logger.error(f"Error validating files: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@document_type_bp.route('/api/document-types/<extension>', methods=['GET'])
def get_document_type_info(extension):
    """Get information about a specific file extension"""
    try:
        # Add dot if not present
        if not extension.startswith('.'):
            extension = '.' + extension
        
        info = document_type_service.get_file_type_info(f"test{extension}")
        
        return jsonify({
            'success': True,
            'file_type_info': info
        })
        
    except Exception as e:
        logger.error(f"Error getting document type info for {extension}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@document_type_bp.route('/api/document-types', methods=['POST'])
def add_document_type():
    """Add a new document type"""
    try:
        data = request.get_json()
        
        extension = data.get('extension')
        mime_type = data.get('mime_type')
        description = data.get('description')
        is_valid = data.get('is_valid', True)
        supports_text_extraction = data.get('supports_text_extraction', True)
        
        if not extension:
            return jsonify({
                'success': False,
                'error': 'extension is required'
            }), 400
        
        success = document_type_service.add_document_type(
            extension=extension,
            mime_type=mime_type,
            description=description,
            is_valid=is_valid,
            supports_text_extraction=supports_text_extraction
        )
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Document type {extension} added/updated successfully'
            })
        else:
            return jsonify({
                'success': False,
                'error': 'Failed to add document type'
            }), 500
            
    except Exception as e:
        logger.error(f"Error adding document type: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@document_type_bp.route('/api/document-types/<extension>/validity', methods=['PUT'])
def update_document_type_validity(extension):
    """Update the validity of a document type"""
    try:
        data = request.get_json()
        is_valid = data.get('is_valid')
        
        if is_valid is None:
            return jsonify({
                'success': False,
                'error': 'is_valid is required'
            }), 400
        
        # Add dot if not present
        if not extension.startswith('.'):
            extension = '.' + extension
        
        success = document_type_service.update_document_type_validity(extension, is_valid)
        
        if success:
            return jsonify({
                'success': True,
                'message': f'Document type {extension} validity updated to {is_valid}'
            })
        else:
            return jsonify({
                'success': False,
                'error': f'Document type {extension} not found'
            }), 404
            
    except Exception as e:
        logger.error(f"Error updating document type validity: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@document_type_bp.route('/api/document-types/refresh-cache', methods=['POST'])
def refresh_cache():
    """Refresh the document types cache"""
    try:
        # Force cache refresh
        document_type_service._valid_extensions_cache = None
        document_type_service._mime_type_cache = None
        document_type_service._refresh_cache()
        
        return jsonify({
            'success': True,
            'message': 'Document types cache refreshed',
            'valid_extensions': document_type_service.get_valid_extensions()
        })
        
    except Exception as e:
        logger.error(f"Error refreshing cache: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500