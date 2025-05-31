"""
Connection API Routes

This module provides REST API endpoints for managing connections.
"""

import logging
from flask import Blueprint, request, jsonify

from services.connection_service import connection_service

logger = logging.getLogger(__name__)

connection_bp = Blueprint('connections', __name__)

@connection_bp.route('/api/connections', methods=['GET'])
def list_connections():
    """List all connections"""
    try:
        connections = connection_service.get_all_connections()
        return jsonify({
            'success': True,
            'connections': connections,
            'total': len(connections)
        }), 200
    except Exception as e:
        logger.error(f"Error listing connections: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@connection_bp.route('/api/connections/<int:connection_id>', methods=['GET'])
def get_connection(connection_id: int):
    """Get a specific connection by ID"""
    try:
        connection = connection_service.get_connection_by_id(connection_id)
        if not connection:
            return jsonify({
                'success': False,
                'error': 'Connection not found'
            }), 404
        
        return jsonify({
            'success': True,
            'connection': connection
        }), 200
    except Exception as e:
        logger.error(f"Error getting connection {connection_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@connection_bp.route('/api/connections', methods=['POST'])
def create_connection():
    """Create a new connection"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        # Validate required fields
        required_fields = ['name', 'provider_id']
        for field in required_fields:
            if field not in data:
                return jsonify({
                    'success': False,
                    'error': f'Missing required field: {field}'
                }), 400
        
        connection = connection_service.create_connection(data)
        return jsonify({
            'success': True,
            'message': 'Connection created successfully',
            'connection': connection
        }), 201
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error creating connection: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@connection_bp.route('/api/connections/<int:connection_id>', methods=['PUT'])
def update_connection(connection_id: int):
    """Update an existing connection"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({
                'success': False,
                'error': 'No data provided'
            }), 400
        
        connection = connection_service.update_connection(connection_id, data)
        if not connection:
            return jsonify({
                'success': False,
                'error': 'Connection not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Connection updated successfully',
            'connection': connection
        }), 200
    except Exception as e:
        logger.error(f"Error updating connection {connection_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@connection_bp.route('/api/connections/<int:connection_id>', methods=['DELETE'])
def delete_connection(connection_id: int):
    """Delete a connection"""
    try:
        success = connection_service.delete_connection(connection_id)
        if not success:
            return jsonify({
                'success': False,
                'error': 'Connection not found'
            }), 404
        
        return jsonify({
            'success': True,
            'message': 'Connection deleted successfully'
        }), 200
    except ValueError as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 400
    except Exception as e:
        logger.error(f"Error deleting connection {connection_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@connection_bp.route('/api/connections/<int:connection_id>/test', methods=['POST'])
def test_connection(connection_id: int):
    """Test a connection"""
    try:
        data = request.get_json() or {}
        success, message = connection_service.test_connection(connection_id, data)
        
        return jsonify({
            'success': success,
            'message': message,
            'connection_status': 'connected' if success else 'failed'
        }), 200
    except Exception as e:
        logger.error(f"Error testing connection {connection_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@connection_bp.route('/api/connections/<int:connection_id>/sync-models', methods=['POST'])
def sync_connection_models(connection_id: int):
    """Sync models for a connection"""
    try:
        success, message = connection_service.sync_models(connection_id)
        
        if success:
            # Get updated connection with new models
            connection = connection_service.get_connection_by_id(connection_id)
            return jsonify({
                'success': True,
                'message': message,
                'connection': connection
            }), 200
        else:
            return jsonify({
                'success': False,
                'error': message
            }), 400
    except Exception as e:
        logger.error(f"Error syncing models for connection {connection_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@connection_bp.route('/api/connections/<int:connection_id>/models', methods=['GET'])
def get_connection_models(connection_id: int):
    """Get available models for a connection"""
    try:
        models = connection_service.get_available_models(connection_id)
        return jsonify({
            'success': True,
            'models': models,
            'total': len(models)
        }), 200
    except Exception as e:
        logger.error(f"Error getting models for connection {connection_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@connection_bp.route('/api/providers/<int:provider_id>/connections', methods=['GET'])
def get_provider_connections(provider_id: int):
    """Get all connections for a specific provider"""
    try:
        connections = connection_service.get_connections_by_provider(provider_id)
        return jsonify({
            'success': True,
            'connections': connections,
            'total': len(connections)
        }), 200
    except Exception as e:
        logger.error(f"Error getting connections for provider {provider_id}: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500
