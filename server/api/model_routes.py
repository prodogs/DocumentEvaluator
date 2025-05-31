"""
Model Management API Routes

This module provides REST API endpoints for managing Models and their
relationships with Service Providers.
"""

import logging
from flask import Blueprint, request, jsonify

from server.services.model_service import model_service
from server.services.model_normalization_service import model_normalization_service

logger = logging.getLogger(__name__)

model_bp = Blueprint('model', __name__)

@model_bp.route('/api/models', methods=['GET'])
def get_all_models():
    """Get all models"""
    try:
        models = model_service.get_all_models()
        return jsonify({
            'success': True,
            'models': models,
            'count': len(models)
        }), 200
    except Exception as e:
        logger.error(f"Error getting models: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@model_bp.route('/api/models/<int:model_id>', methods=['GET'])
def get_model(model_id: int):
    """Get a specific model by ID"""
    try:
        model = model_service.get_model_by_id(model_id)
        if not model:
            return jsonify({
                'success': False,
                'error': 'Model not found'
            }), 404
        
        return jsonify({
            'success': True,
            'model': model
        }), 200
    except Exception as e:
        logger.error(f"Error getting model {model_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@model_bp.route('/api/models', methods=['POST'])
def create_model():
    """Create a new model"""
    try:
        data = request.get_json()
        
        # Validate required fields
        if not data.get('common_name') or not data.get('display_name'):
            return jsonify({
                'success': False,
                'error': 'common_name and display_name are required'
            }), 400
        
        model = model_service.create_model(data)
        return jsonify({
            'success': True,
            'model': model,
            'message': 'Model created successfully'
        }), 201
    except Exception as e:
        logger.error(f"Error creating model: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@model_bp.route('/api/models/<int:model_id>', methods=['PUT'])
def update_model(model_id: int):
    """Update an existing model"""
    try:
        data = request.get_json()
        
        model = model_service.update_model(model_id, data)
        if not model:
            return jsonify({
                'success': False,
                'error': 'Model not found'
            }), 404
        
        return jsonify({
            'success': True,
            'model': model,
            'message': 'Model updated successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error updating model {model_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@model_bp.route('/api/models/<int:model_id>', methods=['DELETE'])
def delete_model(model_id: int):
    """Delete a model"""
    try:
        success = model_service.delete_model(model_id)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Model not found'
            }), 404

        return jsonify({
            'success': True,
            'message': 'Model deleted successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error deleting model {model_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@model_bp.route('/api/models/<int:model_id>/toggle-global', methods=['PUT'])
def toggle_global_model_status(model_id: int):
    """Toggle the global activation status of a model"""
    try:
        data = request.get_json()
        is_active = data.get('is_globally_active', False)

        success = model_service.toggle_global_model_status(model_id, is_active)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Model not found'
            }), 404

        return jsonify({
            'success': True,
            'message': f"Model {'activated' if is_active else 'deactivated'} globally"
        }), 200
    except Exception as e:
        logger.error(f"Error toggling global model status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@model_bp.route('/api/providers/<int:provider_id>/models', methods=['GET'])
def get_provider_models(provider_id: int):
    """Get all models available through a specific provider"""
    try:
        models = model_service.get_models_by_provider(provider_id)
        return jsonify({
            'success': True,
            'models': models,
            'count': len(models)
        }), 200
    except Exception as e:
        logger.error(f"Error getting models for provider {provider_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@model_bp.route('/api/providers/<int:provider_id>/models/<int:model_id>/toggle', methods=['PUT'])
def toggle_provider_model_status(provider_id: int, model_id: int):
    """Toggle the active status of a model for a specific provider"""
    try:
        data = request.get_json()
        is_active = data.get('is_active', False)
        
        success = model_service.toggle_provider_model_status(provider_id, model_id, is_active)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Provider-model relationship not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': f"Model {'activated' if is_active else 'deactivated'} successfully"
        }), 200
    except Exception as e:
        logger.error(f"Error toggling model status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@model_bp.route('/api/models/normalize', methods=['POST'])
def normalize_model_name():
    """Normalize a provider-specific model name to a common name"""
    try:
        data = request.get_json()
        provider_model_name = data.get('provider_model_name')
        
        if not provider_model_name:
            return jsonify({
                'success': False,
                'error': 'provider_model_name is required'
            }), 400
        
        common_name = model_normalization_service.normalize_model_name(provider_model_name)
        
        return jsonify({
            'success': True,
            'provider_model_name': provider_model_name,
            'common_name': common_name
        }), 200
    except Exception as e:
        logger.error(f"Error normalizing model name: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@model_bp.route('/api/models/<int:model_id>/aliases', methods=['GET'])
def get_model_aliases(model_id: int):
    """Get all aliases for a model"""
    try:
        aliases = model_normalization_service.get_model_aliases(model_id)
        return jsonify({
            'success': True,
            'model_id': model_id,
            'aliases': aliases
        }), 200
    except Exception as e:
        logger.error(f"Error getting aliases for model {model_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@model_bp.route('/api/models/families', methods=['GET'])
def get_model_families():
    """Get all available model families"""
    try:
        families = ['GPT', 'Claude', 'LLaMA', 'Mistral', 'Qwen', 'Gemini', 'PaLM', 'Other']
        return jsonify({
            'success': True,
            'families': families
        }), 200
    except Exception as e:
        logger.error(f"Error getting model families: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
