from flask import Blueprint, jsonify, request
import logging

from services.config import service_config, config_manager
from services.health_monitor import health_monitor
from services.client import service_client
from models import Prompt, Folder, Connection
# LlmResponse model moved to KnowledgeDocuments database
from database import Session

logger = logging.getLogger(__name__)

service_routes = Blueprint('service_routes', __name__)

@service_routes.route('/api/services', methods=['GET'])
def list_services():
    """List all configured services with their status"""
    try:
        services = service_config.list_services()
        health_status = health_monitor.get_all_service_status()

        # Combine service config with health status
        for service_name, service_info in services.items():
            if service_name in health_status:
                service_info.update(health_status[service_name])

        return jsonify({
            'services': services,
            'total_services': len(services),
            'enabled_services': len([s for s in services.values() if s['enabled']])
        }), 200

    except Exception as e:
        logger.error(f"Error listing services: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500








@service_routes.route('/api/services/polling/status', methods=['GET'])
def get_polling_status():
    """Get status polling service status"""
    try:
        from api.status_polling import polling_service

        is_running = polling_service.polling_thread and polling_service.polling_thread.is_alive()

        return jsonify({
            'success': True,
            'polling_status': {
                'running': is_running,
                'poll_interval': polling_service.poll_interval,
                'max_poll_duration': polling_service.max_poll_duration,
                'rag_api_base_url': polling_service.rag_api_base_url
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting polling status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@service_routes.route('/api/services/polling/start', methods=['POST'])
def start_polling():
    """Start the status polling service"""
    try:
        from api.status_polling import polling_service

        # Check if already running
        is_running = polling_service.polling_thread and polling_service.polling_thread.is_alive()
        if is_running:
            return jsonify({
                'success': True,
                'message': 'Status polling service is already running',
                'polling_status': {
                    'running': True,
                    'poll_interval': polling_service.poll_interval,
                    'max_poll_duration': polling_service.max_poll_duration
                }
            }), 200

        # Start the polling service
        polling_service.start_polling()
        logger.info("Status polling service started via API")

        return jsonify({
            'success': True,
            'message': 'Status polling service started successfully',
            'polling_status': {
                'running': True,
                'poll_interval': polling_service.poll_interval,
                'max_poll_duration': polling_service.max_poll_duration
            }
        }), 200

    except Exception as e:
        logger.error(f"Error starting polling service: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@service_routes.route('/api/services/polling/stop', methods=['POST'])
def stop_polling():
    """Stop the status polling service"""
    try:
        from api.status_polling import polling_service

        # Stop the polling service
        polling_service.stop_polling_service()
        logger.info("Status polling service stopped via API")

        return jsonify({
            'success': True,
            'message': 'Status polling service stopped successfully',
            'polling_status': {
                'running': False,
                'poll_interval': polling_service.poll_interval,
                'max_poll_duration': polling_service.max_poll_duration
            }
        }), 200

    except Exception as e:
        logger.error(f"Error stopping polling service: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@service_routes.route('/api/services/<service_name>', methods=['GET'])
def get_service_info(service_name):
    """Get detailed information about a specific service"""
    try:
        config = service_config.get_service(service_name)
        if not config:
            return jsonify({'error': f'Service not found: {service_name}'}), 404

        # Get service info from client
        service_info = service_client.get_service_info(service_name)

        # Get health history
        health_history = health_monitor.get_service_health_history(service_name, 10)

        # Format health history
        formatted_history = []
        for check in health_history:
            formatted_history.append({
                'timestamp': check.timestamp.isoformat(),
                'status': check.status.value,
                'response_time_ms': check.response_time_ms,
                'status_code': check.status_code,
                'error_message': check.error_message
            })

        result = {
            'service': service_info,
            'health_history': formatted_history,
            'configuration': {
                'base_url': config.base_url,
                'port': config.port,
                'timeout': config.timeout,
                'max_retries': config.max_retries,
                'retry_delay': config.retry_delay,
                'health_check_endpoint': config.health_check_endpoint
            }
        }

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error getting service info for {service_name}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/services/<service_name>/health', methods=['GET'])
def check_service_health(service_name):
    """Perform an immediate health check on a service"""
    try:
        config = service_config.get_service(service_name)
        if not config:
            return jsonify({'error': f'Service not found: {service_name}'}), 404

        # Perform immediate health check
        health_check = health_monitor.check_service_now(service_name)

        if not health_check:
            return jsonify({'error': 'Failed to perform health check'}), 500

        result = {
            'service_name': health_check.service_name,
            'status': health_check.status.value,
            'response_time_ms': health_check.response_time_ms,
            'timestamp': health_check.timestamp.isoformat(),
            'status_code': health_check.status_code,
            'error_message': health_check.error_message,
            'details': health_check.details
        }

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error checking health of {service_name}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/services/<service_name>/enable', methods=['POST'])
def enable_service(service_name):
    """Enable a service"""
    try:
        config = service_config.get_service(service_name)
        if not config:
            return jsonify({'error': f'Service not found: {service_name}'}), 404

        service_config.enable_service(service_name)

        return jsonify({
            'message': f'Service {service_name} enabled successfully',
            'service_name': service_name,
            'enabled': True
        }), 200

    except Exception as e:
        logger.error(f"Error enabling service {service_name}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/services/<service_name>/disable', methods=['POST'])
def disable_service(service_name):
    """Disable a service"""
    try:
        config = service_config.get_service(service_name)
        if not config:
            return jsonify({'error': f'Service not found: {service_name}'}), 404

        service_config.disable_service(service_name)

        return jsonify({
            'message': f'Service {service_name} disabled successfully',
            'service_name': service_name,
            'enabled': False
        }), 200

    except Exception as e:
        logger.error(f"Error disabling service {service_name}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/services/<service_name>/test', methods=['POST'])
def test_service_connection(service_name):
    """Test connection to a service"""
    try:
        config = service_config.get_service(service_name)
        if not config:
            return jsonify({'error': f'Service not found: {service_name}'}), 404

        # Test with a simple GET request to health endpoint
        from services.client import RequestMethod
        response = service_client.call_service(
            service_name=service_name,
            endpoint="/health" if service_name == "rag_api" else "/api/health",
            method=RequestMethod.GET,
            timeout=10,
            retry_override=1  # Only try once for test
        )

        result = {
            'service_name': service_name,
            'connection_test': {
                'success': response.success,
                'status_code': response.status_code,
                'response_time_ms': response.response_time_ms,
                'retry_count': response.retry_count,
                'error_message': response.error_message
            },
            'timestamp': health_monitor.get_service_health_history(service_name, 1)[-1].timestamp.isoformat() if health_monitor.get_service_health_history(service_name, 1) else None
        }

        return jsonify(result), 200

    except Exception as e:
        logger.error(f"Error testing service {service_name}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/services/health/summary', methods=['GET'])
def get_health_summary():
    """Get a summary of all service health statuses"""
    try:
        all_status = health_monitor.get_all_service_status()

        summary = {
            'healthy': 0,
            'unhealthy': 0,
            'degraded': 0,
            'unknown': 0,
            'total': len(all_status)
        }

        services_by_status = {
            'healthy': [],
            'unhealthy': [],
            'degraded': [],
            'unknown': []
        }

        for service_name, status_info in all_status.items():
            status = status_info['status']
            summary[status] += 1
            services_by_status[status].append({
                'name': service_name,
                'last_check': status_info['last_check'],
                'avg_response_time_ms': status_info['avg_response_time_ms'],
                'error_message': status_info['error_message']
            })

        # Determine overall health status
        if summary['unhealthy'] == 0 and summary['degraded'] == 0:
            overall_health = 'healthy'
        elif summary['unhealthy'] == 0:
            overall_health = 'degraded'
        else:
            overall_health = 'unhealthy'

        return jsonify({
            'summary': summary,
            'services_by_status': services_by_status,
            'overall_health': overall_health
        }), 200

    except Exception as e:
        logger.error(f"Error getting health summary: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/services/response-times', methods=['GET'])
def get_response_time_analytics():
    """DEPRECATED: Response time analytics - LlmResponse moved to KnowledgeDocuments database"""
    return jsonify({
        'deprecated': True,
        'error': 'Response time analytics service moved to KnowledgeDocuments database',
        'reason': 'llm_responses table moved to separate database',
        'analytics': {
            'total_responses': 0,
            'avg_response_time': 0,
            'min_response_time': 0,
            'max_response_time': 0,
            'status_distribution': {}
        }
    }), 410  # 410 Gone - resource no longer available

@service_routes.route('/api/prompts', methods=['GET'])
def list_prompts():
    """List all prompts with their active status"""
    try:
        session = Session()
        prompts = session.query(Prompt).all()

        prompt_list = []
        for prompt in prompts:
            prompt_list.append({
                'id': prompt.id,
                'prompt_text': prompt.prompt_text,
                'description': prompt.description,
                'active': bool(prompt.active)
            })

        session.close()

        return jsonify({
            'prompts': prompt_list,
            'total': len(prompt_list),
            'active_count': len([p for p in prompt_list if p['active']])
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error listing prompts: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/prompts/<int:prompt_id>/activate', methods=['POST'])
def activate_prompt(prompt_id):
    """Activate a prompt"""
    try:
        session = Session()
        prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()

        if not prompt:
            session.close()
            return jsonify({'error': f'Prompt not found: {prompt_id}'}), 404

        prompt.active = 1
        session.commit()

        # Extract values before closing session
        prompt_text = prompt.prompt_text[:50] + "..." if len(prompt.prompt_text) > 50 else prompt.prompt_text
        session.close()

        logger.info(f"Activated prompt ID {prompt_id}: {prompt_text}")

        return jsonify({
            'message': f'Prompt {prompt_id} activated successfully',
            'prompt_id': prompt_id,
            'active': True
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error activating prompt {prompt_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/prompts/<int:prompt_id>/deactivate', methods=['POST'])
def deactivate_prompt(prompt_id):
    """Deactivate a prompt"""
    try:
        session = Session()
        prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()

        if not prompt:
            session.close()
            return jsonify({'error': f'Prompt not found: {prompt_id}'}), 404

        prompt.active = 0
        session.commit()

        # Extract values before closing session
        prompt_text = prompt.prompt_text[:50] + "..." if len(prompt.prompt_text) > 50 else prompt.prompt_text
        session.close()

        logger.info(f"Deactivated prompt ID {prompt_id}: {prompt_text}")

        return jsonify({
            'message': f'Prompt {prompt_id} deactivated successfully',
            'prompt_id': prompt_id,
            'active': False
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error deactivating prompt {prompt_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/prompts', methods=['POST'])
def create_prompt():
    """Create a new prompt"""
    try:
        data = request.get_json()

        # Validate required fields
        if not data.get('prompt_text'):
            return jsonify({'error': 'Missing required field: prompt_text'}), 400

        session = Session()

        prompt = Prompt(
            prompt_text=data['prompt_text'],
            description=data.get('description', ''),
            active=1 if data.get('active', True) else 0
        )

        session.add(prompt)
        session.commit()

        result = {
            'id': prompt.id,
            'prompt_text': prompt.prompt_text,
            'description': prompt.description,
            'active': bool(prompt.active)
        }

        session.close()
        logger.info(f"Created prompt: {prompt.prompt_text[:50]}...")

        return jsonify({
            'message': 'Prompt created successfully',
            'prompt': result
        }), 201

    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        logger.error(f"Error creating prompt: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/prompts/<int:prompt_id>', methods=['PUT'])
def update_prompt(prompt_id):
    """Update an existing prompt"""
    try:
        data = request.get_json()
        session = Session()

        prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()
        if not prompt:
            session.close()
            return jsonify({'error': f'Prompt not found: {prompt_id}'}), 404

        # Update fields
        if 'prompt_text' in data:
            prompt.prompt_text = data['prompt_text']
        if 'description' in data:
            prompt.description = data['description']
        if 'active' in data:
            prompt.active = 1 if data['active'] else 0

        session.commit()

        result = {
            'id': prompt.id,
            'prompt_text': prompt.prompt_text,
            'description': prompt.description,
            'active': bool(prompt.active)
        }

        session.close()
        logger.info(f"Updated prompt ID {prompt_id}: {prompt.prompt_text[:50]}...")

        return jsonify({
            'message': 'Prompt updated successfully',
            'prompt': result
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        logger.error(f"Error updating prompt {prompt_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/prompts/<int:prompt_id>', methods=['DELETE'])
def delete_prompt(prompt_id):
    """Delete a prompt"""
    try:
        session = Session()
        prompt = session.query(Prompt).filter(Prompt.id == prompt_id).first()

        if not prompt:
            session.close()
            return jsonify({'error': f'Prompt not found: {prompt_id}'}), 404

        # LLM response checking moved to KnowledgeDocuments database
        # Skip LLM response dependency check since data moved to separate database
        responses_count = 0  # LLM response data moved to KnowledgeDocuments database

        prompt_text = prompt.prompt_text[:50] + "..." if len(prompt.prompt_text) > 50 else prompt.prompt_text
        session.delete(prompt)
        session.commit()
        session.close()

        logger.info(f"Deleted prompt ID {prompt_id}: {prompt_text}")

        return jsonify({
            'message': f'Prompt deleted successfully'
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        logger.error(f"Error deleting prompt {prompt_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/llm-configurations', methods=['GET'])
def list_llm_configurations():
    """List all connections (replaces deprecated LLM configurations)"""
    try:
        session = Session()
        # Use raw SQL to get connections with provider information
        from sqlalchemy import text
        configs_result = session.execute(text("""
            SELECT c.id, c.name, c.base_url, m.common_name as model_name,
                   p.provider_type, c.port_no, c.is_active
            FROM connections c
            LEFT JOIN llm_providers p ON c.provider_id = p.id
            LEFT JOIN models m ON c.model_id = m.id
        """))
        configs = configs_result.fetchall()

        config_list = []
        for config in configs:
            config_list.append({
                'id': config[0],
                'llm_name': config[1],  # Use connection name for backward compatibility
                'base_url': config[2],
                'model_name': config[3] or 'default',
                'provider_type': config[4],
                'port_no': config[5],
                'active': bool(config[6])
            })

        session.close()

        return jsonify({
            'llm_configurations': config_list,
            'total': len(config_list),
            'active_count': len([c for c in config_list if c['active']])
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error listing connections (LLM configurations): {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/llm-configurations/<int:config_id>/activate', methods=['POST'])
def activate_llm_configuration(config_id):
    """Activate a connection (replaces deprecated LLM configuration)"""
    try:
        session = Session()
        from models import Connection
        connection = session.query(Connection).filter(Connection.id == config_id).first()

        if not connection:
            session.close()
            return jsonify({'error': f'Connection not found: {config_id}'}), 404

        connection.is_active = True
        session.commit()

        # Extract values before closing session
        connection_name = connection.name
        session.close()

        logger.info(f"Activated connection ID {config_id}: {connection_name}")

        return jsonify({
            'message': f'Connection {config_id} activated successfully',
            'config_id': config_id,
            'llm_name': connection_name,  # For backward compatibility
            'active': True
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error activating connection {config_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/llm-configurations/<int:config_id>/deactivate', methods=['POST'])
def deactivate_llm_configuration(config_id):
    """Deactivate a connection (replaces deprecated LLM configuration)"""
    try:
        session = Session()
        from models import Connection
        connection = session.query(Connection).filter(Connection.id == config_id).first()

        if not connection:
            session.close()
            return jsonify({'error': f'Connection not found: {config_id}'}), 404

        connection.is_active = False
        session.commit()

        # Extract values before closing session
        connection_name = connection.name
        session.close()

        logger.info(f"Deactivated connection ID {config_id}: {connection_name}")

        return jsonify({
            'message': f'Connection {config_id} deactivated successfully',
            'config_id': config_id,
            'llm_name': connection_name,  # For backward compatibility
            'active': False
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error deactivating connection {config_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/llm-configurations', methods=['POST'])
def create_llm_configuration():
    """Create a new connection (replaces deprecated LLM configuration)"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['llm_name', 'base_url', 'provider_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400

        session = Session()

        # Check if connection name already exists
        existing = session.query(Connection).filter(Connection.name == data['llm_name']).first()
        if existing:
            session.close()
            return jsonify({'error': f'Connection with name "{data["llm_name"]}" already exists'}), 400

        # Find provider by type (assuming provider_type maps to provider name)
        from sqlalchemy import text
        provider_result = session.execute(text("""
            SELECT id FROM llm_providers WHERE provider_type = :provider_type LIMIT 1
        """), {'provider_type': data['provider_type']})
        provider_row = provider_result.fetchone()

        if not provider_row:
            session.close()
            return jsonify({'error': f'Provider type "{data["provider_type"]}" not found'}), 400

        connection = Connection(
            name=data['llm_name'],
            base_url=data['base_url'],
            provider_id=provider_row[0],
            api_key=data.get('api_key', ''),
            port_no=data.get('port_no', None),
            is_active=data.get('active', True)
        )

        session.add(connection)
        session.commit()

        result = {
            'id': connection.id,
            'llm_name': connection.name,  # Use connection name for backward compatibility
            'base_url': connection.base_url,
            'model_name': 'default',  # Connections don't store model_name directly
            'provider_type': data['provider_type'],  # Use the original provider_type
            'port_no': connection.port_no,
            'active': bool(connection.is_active)
        }

        session.close()
        logger.info(f"Created connection: {connection.name}")

        return jsonify({
            'message': 'Connection created successfully',
            'config': result
        }), 201

    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        logger.error(f"Error creating LLM configuration: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/llm-configurations/<int:config_id>', methods=['PUT'])
def update_llm_configuration(config_id):
    """Update an existing connection (replaces deprecated LLM configuration)"""
    try:
        data = request.get_json()
        session = Session()

        connection = session.query(Connection).filter(Connection.id == config_id).first()
        if not connection:
            session.close()
            return jsonify({'error': f'Connection not found: {config_id}'}), 404

        # Check if new name conflicts with existing (excluding current record)
        if 'llm_name' in data and data['llm_name'] != connection.name:
            existing = session.query(Connection).filter(
                Connection.name == data['llm_name'],
                Connection.id != config_id
            ).first()
            if existing:
                session.close()
                return jsonify({'error': f'Connection with name "{data["llm_name"]}" already exists'}), 400

        # Update fields
        if 'llm_name' in data:
            connection.name = data['llm_name']
        if 'base_url' in data:
            connection.base_url = data['base_url']
        if 'api_key' in data:
            connection.api_key = data['api_key']
        if 'port_no' in data:
            connection.port_no = data['port_no']
        if 'active' in data:
            connection.is_active = data['active']

        session.commit()

        result = {
            'id': connection.id,
            'llm_name': connection.name,
            'base_url': connection.base_url,
            'model_name': 'default',  # Connections don't store model_name directly
            'provider_type': 'unknown',  # Would need to join with provider to get this
            'port_no': connection.port_no,
            'active': bool(connection.is_active)
        }

        session.close()
        logger.info(f"Updated connection ID {config_id}: {connection.name}")

        return jsonify({
            'message': 'Connection updated successfully',
            'config': result
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        logger.error(f"Error updating LLM configuration {config_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/llm-configurations/<int:config_id>', methods=['DELETE'])
def delete_llm_configuration(config_id):
    """Delete a connection (replaces deprecated LLM configuration)"""
    try:
        session = Session()
        connection = session.query(Connection).filter(Connection.id == config_id).first()

        if not connection:
            session.close()
            return jsonify({'error': f'Connection not found: {config_id}'}), 404

        # LLM response checking moved to KnowledgeDocuments database
        # Skip LLM response dependency check since data moved to separate database
        responses_count = 0  # LLM response data moved to KnowledgeDocuments database

        connection_name = connection.name
        session.delete(connection)
        session.commit()
        session.close()

        logger.info(f"Deleted connection ID {config_id}: {connection_name}")

        return jsonify({
            'message': f'Connection "{connection_name}" deleted successfully'
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        logger.error(f"Error deleting LLM configuration {config_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

# REMOVED: Duplicate connection test route - handled by connection_routes.py
# This route was incorrectly testing via RAG API instead of directly testing provider connections

@service_routes.route('/api/llm-configurations/models', methods=['POST'])
def fetch_available_models():
    """Fetch available models from an LLM provider"""
    import requests
    import time
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Request body is required'}), 400

        base_url = data.get('base_url')
        provider_type = data.get('provider_type', 'ollama')
        api_key = data.get('api_key', '')

        if not base_url:
            return jsonify({'error': 'base_url is required'}), 400

        # Construct the full URL for the models endpoint
        if provider_type.lower() == 'ollama':
            # Ollama models endpoint
            models_url = f"{base_url.rstrip('/')}/api/tags"
        elif provider_type.lower() == 'openai':
            # OpenAI models endpoint
            models_url = f"{base_url.rstrip('/')}/v1/models"
        elif provider_type.lower() == 'anthropic':
            # Anthropic doesn't have a public models endpoint, return known models
            return jsonify({
                'success': True,
                'models': [
                    {'id': 'claude-3-5-sonnet-20241022', 'name': 'Claude 3.5 Sonnet'},
                    {'id': 'claude-3-5-haiku-20241022', 'name': 'Claude 3.5 Haiku'},
                    {'id': 'claude-3-opus-20240229', 'name': 'Claude 3 Opus'},
                    {'id': 'claude-3-sonnet-20240229', 'name': 'Claude 3 Sonnet'},
                    {'id': 'claude-3-haiku-20240307', 'name': 'Claude 3 Haiku'}
                ],
                'provider_type': provider_type
            })
        else:
            # For custom providers, try common endpoints
            models_url = f"{base_url.rstrip('/')}/v1/models"

        # Prepare headers
        headers = {'Content-Type': 'application/json'}
        if api_key:
            if provider_type.lower() == 'openai':
                headers['Authorization'] = f'Bearer {api_key}'
            elif provider_type.lower() == 'anthropic':
                headers['x-api-key'] = api_key

        # Make the request with timeout
        start_time = time.time()
        try:
            response = requests.get(models_url, headers=headers, timeout=10)
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)

            if response.status_code == 200:
                response_data = response.json()
                models = []

                if provider_type.lower() == 'ollama':
                    # Parse Ollama response format
                    if 'models' in response_data:
                        for model in response_data['models']:
                            models.append({
                                'id': model.get('name', ''),
                                'name': model.get('name', ''),
                                'size': model.get('size', 0),
                                'modified_at': model.get('modified_at', '')
                            })
                elif provider_type.lower() in ['openai', 'custom']:
                    # Parse OpenAI-compatible response format
                    if 'data' in response_data:
                        for model in response_data['data']:
                            models.append({
                                'id': model.get('id', ''),
                                'name': model.get('id', ''),
                                'object': model.get('object', ''),
                                'created': model.get('created', 0)
                            })

                return jsonify({
                    'success': True,
                    'models': models,
                    'response_time_ms': response_time,
                    'provider_type': provider_type,
                    'total_models': len(models)
                })
            else:
                return jsonify({
                    'success': False,
                    'error': f'HTTP {response.status_code}: {response.text}',
                    'response_time_ms': response_time,
                    'provider_type': provider_type
                }), 400

        except requests.exceptions.ConnectionError:
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            return jsonify({
                'success': False,
                'error': 'Connection failed. Please check the base URL and ensure the service is running.',
                'response_time_ms': response_time,
                'provider_type': provider_type
            }), 400

        except requests.exceptions.Timeout:
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)
            return jsonify({
                'success': False,
                'error': 'Request timed out. The service may be slow or unavailable.',
                'response_time_ms': response_time,
                'provider_type': provider_type
            }), 400

    except Exception as e:
        logger.error(f"Error fetching available models: {str(e)}")
        return jsonify({'error': str(e)}), 500

# Deprecated endpoint removed - now handled by llm_responses_routes.py
# @service_routes.route('/api/llm-responses', methods=['GET'])
# def list_llm_responses():
#     """DEPRECATED: LLM responses listing - LlmResponse moved to KnowledgeDocuments database"""
#     return jsonify({
#         'deprecated': True,
#         'error': 'LLM responses listing service moved to KnowledgeDocuments database',
#         'reason': 'llm_responses table moved to separate database',
#         'responses': [],
#         'total_count': 0
#     }), 410  # 410 Gone - resource no longer available

@service_routes.route('/api/folders', methods=['GET'])
def list_folders():
    """List all folders with their active status"""
    try:
        session = Session()
        folders = session.query(Folder).all()

        folder_list = []
        for folder in folders:
            folder_list.append({
                'id': folder.id,
                'folder_path': folder.folder_path,
                'folder_name': folder.folder_name,
                'active': bool(folder.active),
                'status': getattr(folder, 'status', 'NOT_PROCESSED'),  # Include preprocessing status
                'created_at': folder.created_at.isoformat() if folder.created_at else None
            })

        session.close()

        return jsonify({
            'folders': folder_list,
            'total': len(folder_list),
            'active_count': len([f for f in folder_list if f['active']])
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error listing folders: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/folders/<int:folder_id>/activate', methods=['POST'])
def activate_folder(folder_id):
    """Activate a folder"""
    try:
        session = Session()
        folder = session.query(Folder).filter(Folder.id == folder_id).first()

        if not folder:
            session.close()
            return jsonify({'error': f'Folder not found: {folder_id}'}), 404

        # Check if folder has been preprocessed
        folder_status = getattr(folder, 'status', 'NOT_PROCESSED')
        if folder_status != 'READY':
            session.close()
            return jsonify({
                'error': f'Folder must be preprocessed before activation. Current status: {folder_status}. Please preprocess the folder first.'
            }), 400

        folder.active = 1
        session.commit()

        # Get folder path before closing session
        folder_path = folder.folder_path
        session.close()

        logger.info(f"Activated folder ID {folder_id}: {folder_path}")

        return jsonify({
            'message': f'Folder {folder_id} activated successfully',
            'folder_id': folder_id,
            'folder_path': folder_path,
            'active': True
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error activating folder {folder_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/folders/<int:folder_id>/deactivate', methods=['POST'])
def deactivate_folder(folder_id):
    """Deactivate a folder"""
    try:
        session = Session()
        folder = session.query(Folder).filter(Folder.id == folder_id).first()

        if not folder:
            session.close()
            return jsonify({'error': f'Folder not found: {folder_id}'}), 404

        folder.active = 0
        session.commit()

        # Get folder path before closing session
        folder_path = folder.folder_path
        session.close()

        logger.info(f"Deactivated folder ID {folder_id}: {folder_path}")

        return jsonify({
            'message': f'Folder {folder_id} deactivated successfully',
            'folder_id': folder_id,
            'folder_path': folder_path,
            'active': False
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error deactivating folder {folder_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/config/document-processing', methods=['GET'])
def get_document_processing_config():
    """Get current document processing configuration"""
    try:
        doc_config = config_manager.get_document_config()

        return jsonify({
            'success': True,
            'config': {
                'max_file_size_mb': doc_config.max_file_size_mb,
                'max_file_size_bytes': doc_config.max_file_size_bytes,
                'max_file_size_display': doc_config.max_file_size_display,
                'min_file_size_bytes': doc_config.min_file_size_bytes
            }
        }), 200

    except Exception as e:
        logger.error(f"Error getting document processing config: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

def register_service_routes(app):
    """Register service management routes with the Flask app"""
    app.register_blueprint(service_routes)
    logger.info("Service management routes registered")
    return app
