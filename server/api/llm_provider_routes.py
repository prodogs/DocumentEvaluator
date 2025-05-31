"""
LLM Provider Management API Routes

Provides REST API endpoints for managing LLM providers, models, and configurations.
"""

from flask import Blueprint, request, jsonify
import logging
from typing import Dict, Any

from server.services.llm_provider_service import llm_provider_service
from server.database import Session
from server.models import LlmProvider, LlmModel, LlmConfiguration

logger = logging.getLogger(__name__)

llm_provider_bp = Blueprint('llm_provider', __name__)

@llm_provider_bp.route('/api/llm-providers', methods=['GET'])
def get_providers():
    """Get all LLM providers"""
    try:
        providers = llm_provider_service.get_all_providers()
        return jsonify({
            'success': True,
            'providers': providers
        }), 200
    except Exception as e:
        logger.error(f"Error getting providers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_provider_bp.route('/api/llm-providers/<int:provider_id>', methods=['GET'])
def get_provider(provider_id: int):
    """Get a specific provider by ID"""
    try:
        provider = llm_provider_service.get_provider_by_id(provider_id)
        if not provider:
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        return jsonify({
            'success': True,
            'provider': provider
        }), 200
    except Exception as e:
        logger.error(f"Error getting provider {provider_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_provider_bp.route('/api/llm-providers', methods=['POST'])
def create_provider():
    """Create a new LLM provider"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['name', 'provider_type']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        provider = llm_provider_service.create_provider(data)
        return jsonify({
            'success': True,
            'message': 'Provider created successfully',
            'provider': provider
        }), 201
    except Exception as e:
        logger.error(f"Error creating provider: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_provider_bp.route('/api/llm-providers/<int:provider_id>', methods=['PUT'])
def update_provider(provider_id: int):
    """Update an existing provider"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        provider = llm_provider_service.update_provider(provider_id, data)
        if not provider:
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Provider updated successfully',
            'provider': provider
        }), 200
    except Exception as e:
        logger.error(f"Error updating provider {provider_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_provider_bp.route('/api/llm-providers/<int:provider_id>', methods=['DELETE'])
def delete_provider(provider_id: int):
    """Delete a provider"""
    try:
        success = llm_provider_service.delete_provider(provider_id)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Provider deleted successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error deleting provider {provider_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_provider_bp.route('/api/llm-providers/<int:provider_id>/test-connection', methods=['POST'])
def test_provider_connection(provider_id: int):
    """Test connection to a provider"""
    try:
        data = request.get_json() or {}
        
        # Get provider configuration
        provider = llm_provider_service.get_provider_by_id(provider_id)
        if not provider:
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        # Merge provider data with request data for testing
        config = {
            'provider_type': provider['provider_type'],
            **data
        }
        
        success, message = llm_provider_service.test_connection(config)
        
        return jsonify({
            'success': success,
            'message': message,
            'connected': success
        }), 200 if success else 400
    except Exception as e:
        logger.error(f"Error testing connection for provider {provider_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_provider_bp.route('/api/llm-providers/<int:provider_id>/discover-models', methods=['POST'])
def discover_provider_models(provider_id: int):
    """Discover available models from a provider"""
    try:
        data = request.get_json() or {}
        
        # Get provider
        provider = llm_provider_service.get_provider_by_id(provider_id)
        if not provider:
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        # Merge provider data with request data
        config = {
            'provider_type': provider['provider_type'],
            **data
        }
        
        success, models, error = llm_provider_service.discover_models(provider_id, config)
        
        if success:
            return jsonify({
                'success': True,
                'models': models,
                'count': len(models)
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': error
            }), 400
    except Exception as e:
        logger.error(f"Error discovering models for provider {provider_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_provider_bp.route('/api/llm-providers/<int:provider_id>/models', methods=['GET'])
def get_provider_models(provider_id: int):
    """Get all models for a provider"""
    try:
        models = llm_provider_service.get_provider_models(provider_id)
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

@llm_provider_bp.route('/api/llm-providers/<int:provider_id>/models/<int:model_id>/toggle', methods=['PUT'])
def toggle_model_status(provider_id: int, model_id: int):
    """Toggle the active status of a model"""
    try:
        data = request.get_json() or {}
        is_active = data.get('is_active', False)
        
        success = llm_provider_service.toggle_model_status(model_id, is_active)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Model not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': f'Model {"activated" if is_active else "deactivated"} successfully'
        }), 200
    except Exception as e:
        logger.error(f"Error toggling model {model_id} status: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_provider_bp.route('/api/llm-providers/<int:provider_id>/sync-models', methods=['POST'])
def sync_provider_models(provider_id: int):
    """Sync models for a provider"""
    try:
        success, message = llm_provider_service.sync_models(provider_id)
        
        if success:
            return jsonify({
                'success': True,
                'message': message
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
    except Exception as e:
        logger.error(f"Error syncing models for provider {provider_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_provider_bp.route('/api/llm-providers/types', methods=['GET'])
def get_provider_types():
    """Get available provider types"""
    try:
        provider_types = [
            {
                'type': 'ollama',
                'name': 'Ollama',
                'description': 'Local LLM service',
                'auth_type': 'none',
                'supports_discovery': True
            },
            {
                'type': 'openai',
                'name': 'OpenAI',
                'description': 'OpenAI API service',
                'auth_type': 'api_key',
                'supports_discovery': True
            },
            {
                'type': 'lmstudio',
                'name': 'LM Studio',
                'description': 'Local LM Studio server',
                'auth_type': 'none',
                'supports_discovery': True
            },
            {
                'type': 'amazon',
                'name': 'Amazon Bedrock',
                'description': 'AWS Bedrock service',
                'auth_type': 'aws_credentials',
                'supports_discovery': False
            },
            {
                'type': 'grok',
                'name': 'Grok (X.AI)',
                'description': 'Grok API service',
                'auth_type': 'api_key',
                'supports_discovery': True
            }
        ]
        
        return jsonify({
            'success': True,
            'provider_types': provider_types
        }), 200
    except Exception as e:
        logger.error(f"Error getting provider types: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@llm_provider_bp.route('/api/llm-providers/<int:provider_id>/default-config', methods=['GET'])
def get_provider_default_config(provider_id: int):
    """Get default configuration for a provider"""
    try:
        provider = llm_provider_service.get_provider_by_id(provider_id)
        if not provider:
            return jsonify({
                'success': False,
                'error': 'Provider not found'
            }), 404
        
        # Get default config from provider adapter
        provider_type = provider['provider_type']
        if provider_type in llm_provider_service.provider_adapters:
            adapter = llm_provider_service.provider_adapters[provider_type]
            default_config = adapter.get_default_config()
            
            return jsonify({
                'success': True,
                'default_config': default_config
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': f'Provider type {provider_type} not supported'
            }), 400
    except Exception as e:
        logger.error(f"Error getting default config for provider {provider_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
