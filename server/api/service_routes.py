from flask import Blueprint, jsonify, request
import logging

from server.services.config import service_config
from server.services.health_monitor import health_monitor
from server.services.client import service_client
from server.models import LlmResponse, Prompt, LlmConfiguration, Folder
from server.database import Session

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


@service_routes.route('/api/services/queue/status', methods=['GET'])
def get_queue_status():
    """Get dynamic processing queue status"""
    try:
        from server.services.dynamic_processing_queue import dynamic_queue

        status = dynamic_queue.get_queue_status()

        return jsonify({
            'success': True,
            'queue_status': status
        }), 200

    except Exception as e:
        logger.error(f"Error getting queue status: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@service_routes.route('/api/services/queue/start', methods=['POST'])
def start_queue():
    """Start the dynamic processing queue"""
    try:
        from server.services.dynamic_processing_queue import dynamic_queue

        # Check if already running
        status = dynamic_queue.get_queue_status()
        if status['queue_running']:
            return jsonify({
                'success': True,
                'message': 'Dynamic processing queue is already running',
                'queue_status': status
            }), 200

        # Start the queue
        dynamic_queue.start_queue_processing()
        logger.info("Dynamic processing queue started via API")

        # Get updated status
        updated_status = dynamic_queue.get_queue_status()

        return jsonify({
            'success': True,
            'message': 'Dynamic processing queue started successfully',
            'queue_status': updated_status
        }), 200

    except Exception as e:
        logger.error(f"Error starting queue: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@service_routes.route('/api/services/queue/stop', methods=['POST'])
def stop_queue():
    """Stop the dynamic processing queue"""
    try:
        from server.services.dynamic_processing_queue import dynamic_queue

        # Stop the queue
        dynamic_queue.stop_queue_processing()
        logger.info("Dynamic processing queue stopped via API")

        # Get updated status
        updated_status = dynamic_queue.get_queue_status()

        return jsonify({
            'success': True,
            'message': 'Dynamic processing queue stopped successfully',
            'queue_status': updated_status
        }), 200

    except Exception as e:
        logger.error(f"Error stopping queue: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@service_routes.route('/api/services/polling/status', methods=['GET'])
def get_polling_status():
    """Get status polling service status"""
    try:
        from server.api.status_polling import polling_service

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
        from server.api.status_polling import polling_service

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
        from server.api.status_polling import polling_service

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
        from server.services.client import RequestMethod
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
    """Get response time analytics for analyze_document_with_llm requests"""
    try:
        session = Session()

        # Get query parameters
        limit = request.args.get('limit', 50, type=int)
        status_filter = request.args.get('status', None)  # Optional status filter (P, S, F)

        # Build query
        query = session.query(LlmResponse).filter(
            LlmResponse.response_time_ms.isnot(None),
            LlmResponse.response_time_ms > 0
        )

        if status_filter:
            query = query.filter(LlmResponse.status == status_filter.upper())

        # Get recent records ordered by timestamp
        recent_responses = query.order_by(LlmResponse.timestamp.desc()).limit(limit).all()

        if not recent_responses:
            return jsonify({
                'message': 'No response time data available',
                'analytics': {
                    'total_requests': 0,
                    'avg_response_time_ms': 0,
                    'min_response_time_ms': 0,
                    'max_response_time_ms': 0,
                    'median_response_time_ms': 0
                },
                'recent_requests': []
            }), 200

        # Calculate analytics
        response_times = [r.response_time_ms for r in recent_responses]
        total_requests = len(response_times)
        avg_response_time = sum(response_times) / total_requests
        min_response_time = min(response_times)
        max_response_time = max(response_times)

        # Calculate median
        sorted_times = sorted(response_times)
        n = len(sorted_times)
        if n % 2 == 0:
            median_response_time = (sorted_times[n//2 - 1] + sorted_times[n//2]) / 2
        else:
            median_response_time = sorted_times[n//2]

        # Format recent requests with LLM configuration and prompt details
        recent_requests = []
        for response in recent_responses:
            # Get LLM configuration details if available
            llm_config_details = None
            if response.llm_config_id and response.llm_config:
                llm_config_details = {
                    'id': response.llm_config.id,
                    'llm_name': response.llm_config.llm_name,
                    'model_name': response.llm_config.model_name,
                    'provider_type': response.llm_config.provider_type,
                    'base_url': response.llm_config.base_url,
                    'active': bool(response.llm_config.active)
                }

            # Get prompt details if available
            prompt_details = None
            if response.prompt:
                prompt_details = {
                    'id': response.prompt.id,
                    'prompt_text': response.prompt.prompt_text[:100] + '...' if len(response.prompt.prompt_text) > 100 else response.prompt.prompt_text,
                    'description': response.prompt.description,
                    'active': bool(response.prompt.active)
                }

            recent_requests.append({
                'id': response.id,
                'task_id': response.task_id,
                'document_id': response.document_id,
                'llm_name': response.llm_name,  # Keep for backward compatibility
                'llm_config': llm_config_details,
                'prompt': prompt_details,
                'status': response.status,
                'response_time_ms': response.response_time_ms,
                'timestamp': response.timestamp.isoformat() if response.timestamp else None,
                'error_message': response.error_message[:100] + '...' if response.error_message and len(response.error_message) > 100 else response.error_message
            })

        # Status breakdown
        status_breakdown = {}
        for response in recent_responses:
            status = response.status
            if status not in status_breakdown:
                status_breakdown[status] = {'count': 0, 'avg_response_time_ms': 0, 'response_times': []}
            status_breakdown[status]['count'] += 1
            status_breakdown[status]['response_times'].append(response.response_time_ms)

        # Calculate averages for each status
        for status, data in status_breakdown.items():
            if data['response_times']:
                data['avg_response_time_ms'] = round(sum(data['response_times']) / len(data['response_times']), 2)
            del data['response_times']  # Remove raw data from response

        session.close()

        return jsonify({
            'analytics': {
                'total_requests': total_requests,
                'avg_response_time_ms': round(avg_response_time, 2),
                'min_response_time_ms': min_response_time,
                'max_response_time_ms': max_response_time,
                'median_response_time_ms': round(median_response_time, 2),
                'status_breakdown': status_breakdown
            },
            'recent_requests': recent_requests,
            'query_params': {
                'limit': limit,
                'status_filter': status_filter
            }
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error getting response time analytics: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

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

        # Check if prompt is being used in any LLM responses
        from server.models import LlmResponse
        responses_count = session.query(LlmResponse).filter(LlmResponse.prompt_id == prompt_id).count()

        if responses_count > 0:
            session.close()
            return jsonify({
                'error': f'Cannot delete prompt: it is referenced by {responses_count} LLM responses'
            }), 400

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
    """List all LLM configurations with their active status"""
    try:
        session = Session()
        configs = session.query(LlmConfiguration).all()

        config_list = []
        for config in configs:
            config_list.append({
                'id': config.id,
                'llm_name': config.llm_name,
                'base_url': config.base_url,
                'model_name': config.model_name,
                'provider_type': config.provider_type,
                'port_no': config.port_no,
                'active': bool(config.active)
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
        logger.error(f"Error listing LLM configurations: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/llm-configurations/<int:config_id>/activate', methods=['POST'])
def activate_llm_configuration(config_id):
    """Activate an LLM configuration"""
    try:
        session = Session()
        config = session.query(LlmConfiguration).filter(LlmConfiguration.id == config_id).first()

        if not config:
            session.close()
            return jsonify({'error': f'LLM configuration not found: {config_id}'}), 404

        config.active = 1
        session.commit()

        # Extract values before closing session
        llm_name = config.llm_name
        session.close()

        logger.info(f"Activated LLM configuration ID {config_id}: {llm_name}")

        return jsonify({
            'message': f'LLM configuration {config_id} activated successfully',
            'config_id': config_id,
            'llm_name': llm_name,
            'active': True
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error activating LLM configuration {config_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/llm-configurations/<int:config_id>/deactivate', methods=['POST'])
def deactivate_llm_configuration(config_id):
    """Deactivate an LLM configuration"""
    try:
        session = Session()
        config = session.query(LlmConfiguration).filter(LlmConfiguration.id == config_id).first()

        if not config:
            session.close()
            return jsonify({'error': f'LLM configuration not found: {config_id}'}), 404

        config.active = 0
        session.commit()

        # Extract values before closing session
        llm_name = config.llm_name
        session.close()

        logger.info(f"Deactivated LLM configuration ID {config_id}: {llm_name}")

        return jsonify({
            'message': f'LLM configuration {config_id} deactivated successfully',
            'config_id': config_id,
            'llm_name': llm_name,
            'active': False
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error deactivating LLM configuration {config_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/llm-configurations', methods=['POST'])
def create_llm_configuration():
    """Create a new LLM configuration"""
    try:
        data = request.get_json()

        # Validate required fields
        required_fields = ['llm_name', 'base_url', 'model_name', 'provider_type']
        for field in required_fields:
            if not data.get(field):
                return jsonify({'error': f'Missing required field: {field}'}), 400

        session = Session()

        # Check if llm_name already exists
        existing = session.query(LlmConfiguration).filter(LlmConfiguration.llm_name == data['llm_name']).first()
        if existing:
            session.close()
            return jsonify({'error': f'LLM configuration with name "{data["llm_name"]}" already exists'}), 400

        config = LlmConfiguration(
            llm_name=data['llm_name'],
            base_url=data['base_url'],
            model_name=data['model_name'],
            provider_type=data['provider_type'],
            api_key=data.get('api_key', ''),
            port_no=data.get('port_no', 0),
            active=1 if data.get('active', True) else 0
        )

        session.add(config)
        session.commit()

        result = {
            'id': config.id,
            'llm_name': config.llm_name,
            'base_url': config.base_url,
            'model_name': config.model_name,
            'provider_type': config.provider_type,
            'port_no': config.port_no,
            'active': bool(config.active)
        }

        session.close()
        logger.info(f"Created LLM configuration: {config.llm_name}")

        return jsonify({
            'message': 'LLM configuration created successfully',
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
    """Update an existing LLM configuration"""
    try:
        data = request.get_json()
        session = Session()

        config = session.query(LlmConfiguration).filter(LlmConfiguration.id == config_id).first()
        if not config:
            session.close()
            return jsonify({'error': f'LLM configuration not found: {config_id}'}), 404

        # Check if new llm_name conflicts with existing (excluding current record)
        if 'llm_name' in data and data['llm_name'] != config.llm_name:
            existing = session.query(LlmConfiguration).filter(
                LlmConfiguration.llm_name == data['llm_name'],
                LlmConfiguration.id != config_id
            ).first()
            if existing:
                session.close()
                return jsonify({'error': f'LLM configuration with name "{data["llm_name"]}" already exists'}), 400

        # Update fields
        if 'llm_name' in data:
            config.llm_name = data['llm_name']
        if 'base_url' in data:
            config.base_url = data['base_url']
        if 'model_name' in data:
            config.model_name = data['model_name']
        if 'provider_type' in data:
            config.provider_type = data['provider_type']
        if 'api_key' in data:
            config.api_key = data['api_key']
        if 'port_no' in data:
            config.port_no = data['port_no']
        if 'active' in data:
            config.active = 1 if data['active'] else 0

        session.commit()

        result = {
            'id': config.id,
            'llm_name': config.llm_name,
            'base_url': config.base_url,
            'model_name': config.model_name,
            'provider_type': config.provider_type,
            'port_no': config.port_no,
            'active': bool(config.active)
        }

        session.close()
        logger.info(f"Updated LLM configuration ID {config_id}: {config.llm_name}")

        return jsonify({
            'message': 'LLM configuration updated successfully',
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
    """Delete an LLM configuration"""
    try:
        session = Session()
        config = session.query(LlmConfiguration).filter(LlmConfiguration.id == config_id).first()

        if not config:
            session.close()
            return jsonify({'error': f'LLM configuration not found: {config_id}'}), 404

        # Check if configuration is being used in any LLM responses
        from server.models import LlmResponse
        responses_count = session.query(LlmResponse).filter(LlmResponse.llm_config_id == config_id).count()

        if responses_count > 0:
            session.close()
            return jsonify({
                'error': f'Cannot delete LLM configuration: it is referenced by {responses_count} LLM responses'
            }), 400

        llm_name = config.llm_name
        session.delete(config)
        session.commit()
        session.close()

        logger.info(f"Deleted LLM configuration ID {config_id}: {llm_name}")

        return jsonify({
            'message': f'LLM configuration "{llm_name}" deleted successfully'
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.rollback()
            session.close()
        logger.error(f"Error deleting LLM configuration {config_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@service_routes.route('/api/llm-configurations/<int:config_id>/test', methods=['POST'])
def test_llm_configuration(config_id):
    """Test an LLM configuration by making a test call"""
    import time
    try:
        session = Session()
        config = session.query(LlmConfiguration).filter(LlmConfiguration.id == config_id).first()

        if not config:
            session.close()
            return jsonify({'error': f'LLM configuration not found: {config_id}'}), 404

        config_dict = {
            'id': config.id,
            'llm_name': config.llm_name,
            'base_url': config.base_url,
            'model_name': config.model_name,
            'provider_type': config.provider_type,
            'api_key': config.api_key,
            'port_no': config.port_no
        }

        session.close()

        # Import the RAG service client
        from server.services.client import RAGServiceClient, RequestMethod
        import json

        # Create RAG service client instance
        rag_client = RAGServiceClient()

        # Test prompt
        test_prompt = "Hello! This is a test message. Please respond with 'Test successful' if you can read this."

        # Create a simple test document content
        test_content = "This is a test document for validating LLM configuration."
        test_filename = "test_config.txt"

        # Prepare data for RAG service
        prompts_data = [{'prompt': test_prompt}]
        llm_provider_data = {
            'provider_type': config_dict['provider_type'],
            'url': config_dict['base_url'],
            'model_name': config_dict['model_name'],
            'api_key': config_dict['api_key'],
            'port_no': config_dict['port_no']
        }

        # Make test call
        start_time = time.time()
        try:
            response = rag_client.client.call_service(
                service_name="rag_api",
                endpoint="/analyze_document_with_llm",
                method=RequestMethod.POST,
                data={
                    'filename': test_filename,
                    'prompts': json.dumps(prompts_data),
                    'llm_provider': json.dumps(llm_provider_data)
                },
                files={
                    'file': (test_filename, test_content.encode('utf-8'), 'text/plain')
                },
                timeout=30
            )

            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)

            if response.success:
                return jsonify({
                    'success': True,
                    'message': 'LLM configuration test successful',
                    'response': response.data,
                    'response_time_ms': response_time,
                    'config_name': config_dict['llm_name'],
                    'model_name': config_dict['model_name'],
                    'provider_type': config_dict['provider_type']
                })
            else:
                return jsonify({
                    'success': False,
                    'message': 'LLM configuration test failed',
                    'error': response.error_message,
                    'response_time_ms': response_time,
                    'config_name': config_dict['llm_name'],
                    'model_name': config_dict['model_name'],
                    'provider_type': config_dict['provider_type']
                }), 400

        except Exception as llm_error:
            end_time = time.time()
            response_time = round((end_time - start_time) * 1000, 2)

            return jsonify({
                'success': False,
                'message': 'LLM configuration test failed',
                'error': str(llm_error),
                'response_time_ms': response_time,
                'config_name': config_dict['llm_name'],
                'model_name': config_dict['model_name'],
                'provider_type': config_dict['provider_type']
            }), 400

    except Exception as e:
        logger.error(f"Error testing LLM configuration {config_id}: {str(e)}")
        return jsonify({'error': str(e)}), 500

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

@service_routes.route('/api/llm-responses', methods=['GET'])
def list_llm_responses():
    """List LLM responses with full prompt and configuration details"""
    try:
        session = Session()

        # Get query parameters
        limit = request.args.get('limit', 20, type=int)
        status_filter = request.args.get('status', None)

        # Build query with joins to get full details
        query = session.query(LlmResponse).options(
            # Eagerly load related objects to avoid N+1 queries
            session.query(LlmResponse).join(Prompt).join(LlmConfiguration, LlmResponse.llm_config_id == LlmConfiguration.id)
        )

        if status_filter:
            query = query.filter(LlmResponse.status == status_filter.upper())

        # Get recent responses
        responses = query.order_by(LlmResponse.timestamp.desc()).limit(limit).all()

        response_list = []
        for response in responses:
            # Get prompt details
            prompt_info = None
            if response.prompt:
                prompt_info = {
                    'id': response.prompt.id,
                    'prompt_text': response.prompt.prompt_text,
                    'description': response.prompt.description,
                    'active': bool(response.prompt.active)
                }

            # Get LLM configuration details
            llm_config_info = None
            if response.llm_config_id and response.llm_config:
                llm_config_info = {
                    'id': response.llm_config.id,
                    'llm_name': response.llm_config.llm_name,
                    'model_name': response.llm_config.model_name,
                    'provider_type': response.llm_config.provider_type,
                    'base_url': response.llm_config.base_url,
                    'port_no': response.llm_config.port_no,
                    'active': bool(response.llm_config.active)
                }

            response_list.append({
                'id': response.id,
                'document_id': response.document_id,
                'task_id': response.task_id,
                'status': response.status,
                'prompt': prompt_info,
                'llm_config': llm_config_info,
                'llm_name': response.llm_name,  # Keep for backward compatibility
                'response_time_ms': response.response_time_ms,
                'started_processing_at': response.started_processing_at.isoformat() if response.started_processing_at else None,
                'completed_processing_at': response.completed_processing_at.isoformat() if response.completed_processing_at else None,
                'timestamp': response.timestamp.isoformat() if response.timestamp else None,
                'has_response': bool(response.response_text),
                'has_error': bool(response.error_message),
                'error_message': response.error_message[:200] + '...' if response.error_message and len(response.error_message) > 200 else response.error_message
            })

        session.close()

        return jsonify({
            'responses': response_list,
            'total': len(response_list),
            'query_params': {
                'limit': limit,
                'status_filter': status_filter
            }
        }), 200

    except Exception as e:
        if 'session' in locals():
            session.close()
        logger.error(f"Error listing LLM responses: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

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

def register_service_routes(app):
    """Register service management routes with the Flask app"""
    app.register_blueprint(service_routes)
    logger.info("Service management routes registered")
    return app
