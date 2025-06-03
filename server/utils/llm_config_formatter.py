"""
Unified LLM Configuration Formatter

This module provides a single source of truth for formatting LLM configurations
for the RAG API. This prevents inconsistencies and breaking changes when
formatting LLM provider data.
"""

import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


def format_llm_config_for_rag_api(connection_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Format LLM configuration data for RAG API consumption.
    
    This is the SINGLE SOURCE OF TRUTH for how LLM configurations should be
    formatted when sending to the RAG API.
    
    Args:
        connection_data: Dictionary containing connection information with fields:
            - provider_type: Type of LLM provider (ollama, openai, etc.)
            - base_url: Base URL of the LLM service
            - port_no: Optional port number
            - model_name: Name of the model to use
            - api_key: Optional API key
            
    Returns:
        Dictionary formatted for RAG API with fields:
            - provider_type: Type of LLM provider
            - base_url: Complete URL including port
            - model_name: Name of the model
            - api_key: Optional API key
            
    Example:
        Input: {
            'provider_type': 'ollama',
            'base_url': 'http://studio.local',
            'port_no': 11434,
            'model_name': 'gemma3:latest'
        }
        Output: {
            'provider_type': 'ollama',
            'base_url': 'http://studio.local:11434',
            'model_name': 'gemma3:latest'
        }
    """
    # Extract fields with safe defaults
    provider_type = connection_data.get('provider_type', 'ollama')
    base_url = connection_data.get('base_url', 'http://localhost')
    port_no = connection_data.get('port_no')
    model_name = connection_data.get('model_name')
    api_key = connection_data.get('api_key')
    
    # Fallback: if model_name is missing but model_id exists, try to look it up
    if not model_name and connection_data.get('model_id'):
        try:
            from database import Session
            from models import Model
            session = Session()
            model = session.query(Model).filter_by(id=connection_data['model_id']).first()
            if model:
                model_name = model.display_name
                logger.info(f"Resolved model_id {connection_data['model_id']} to model_name '{model_name}'")
            session.close()
        except Exception as e:
            logger.warning(f"Failed to resolve model_id {connection_data.get('model_id')}: {e}")
    
    # Final fallback to 'default' if no model name found
    if not model_name:
        model_name = 'default'
        logger.warning("No model_name or resolvable model_id found, using 'default'")
    
    # Build complete URL
    url = build_complete_url(base_url, port_no)
    
    # Build config dictionary
    # NOTE: RAG API expects 'base_url' field (not 'url')
    config = {
        'provider_type': provider_type,
        'base_url': url,  # RAG API expects 'base_url' field
        'model_name': model_name
    }
    
    # Only include api_key if it exists
    if api_key:
        config['api_key'] = api_key
    
    logger.debug(f"Formatted LLM config: provider={provider_type}, url={url}, model={model_name}")
    
    return config


def build_complete_url(base_url: str, port: Optional[int]) -> str:
    """
    Build a complete URL from base URL and optional port.
    
    Args:
        base_url: Base URL (may or may not include port)
        port: Optional port number
        
    Returns:
        Complete URL with port if needed
        
    Examples:
        ('http://localhost', 11434) -> 'http://localhost:11434'
        ('http://localhost:11434', 11434) -> 'http://localhost:11434'
        ('http://localhost:8080', 11434) -> 'http://localhost:8080'
        ('studio.local', 11434) -> 'studio.local:11434'
    """
    if not base_url:
        base_url = 'http://localhost'
    
    # If no port specified, return base_url as-is
    if not port:
        return base_url
    
    # Check if port is already in the URL
    if f':{port}' in base_url:
        return base_url
    
    # Check if any port is already specified
    if '://' in base_url:
        # Split protocol and rest
        protocol, rest = base_url.split('://', 1)
        if ':' in rest and '/' not in rest.split(':', 1)[1]:
            # Port already exists in URL, return as-is
            return base_url
        else:
            # No port in URL, add it
            host = rest.split('/')[0]
            path = '/' + '/'.join(rest.split('/')[1:]) if '/' in rest else ''
            return f"{protocol}://{host}:{port}{path}"
    else:
        # No protocol, just host
        if ':' in base_url:
            # Port might already exist
            return base_url
        else:
            # Add port
            return f"{base_url}:{port}"


def validate_llm_config(config: Dict[str, Any]) -> bool:
    """
    Validate that LLM configuration has required fields.
    
    Args:
        config: LLM configuration dictionary
        
    Returns:
        True if valid, False otherwise
    """
    required_fields = ['provider_type', 'base_url', 'model_name']
    
    for field in required_fields:
        if field not in config or not config[field]:
            logger.error(f"Missing required field in LLM config: {field}")
            return False
    
    return True