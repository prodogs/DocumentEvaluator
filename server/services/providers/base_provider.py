"""
Base Provider Class

Abstract base class for all LLM provider adapters.
Each provider adapter must implement the methods defined here.
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Tuple
import logging

logger = logging.getLogger(__name__)

class BaseLLMProvider(ABC):
    """Abstract base class for LLM provider adapters"""
    
    def __init__(self, provider_type: str):
        self.provider_type = provider_type
        self.logger = logging.getLogger(f"{__name__}.{provider_type}")
    
    @abstractmethod
    def test_connection(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Test connection to the provider
        
        Args:
            config: Provider configuration including base_url, api_key, etc.
            
        Returns:
            Tuple of (success: bool, message: str)
        """
        pass
    
    @abstractmethod
    def discover_models(self, config: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]], str]:
        """
        Discover available models from the provider
        
        Args:
            config: Provider configuration including base_url, api_key, etc.
            
        Returns:
            Tuple of (success: bool, models: List[Dict], error_message: str)
            
        Model dictionary should contain:
        - model_name: Human-readable model name
        - model_id: Provider-specific model identifier
        - capabilities: Optional dict with model capabilities
        """
        pass
    
    @abstractmethod
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Validate provider configuration
        
        Args:
            config: Provider configuration to validate
            
        Returns:
            Tuple of (is_valid: bool, error_message: str)
        """
        pass
    
    def get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration for this provider
        
        Returns:
            Dictionary with default configuration values
        """
        return {
            'provider_type': self.provider_type,
            'base_url': '',
            'api_key': '',
            'port_no': None
        }
    
    def format_error_message(self, error: Exception) -> str:
        """
        Format error message for consistent error reporting
        
        Args:
            error: Exception that occurred
            
        Returns:
            Formatted error message string
        """
        return f"{self.provider_type.title()} Error: {str(error)}"
    
    def log_connection_attempt(self, config: Dict[str, Any]):
        """Log connection attempt (without sensitive data)"""
        safe_config = {k: v for k, v in config.items() if k != 'api_key'}
        if 'api_key' in config and config['api_key']:
            safe_config['api_key'] = '***masked***'
        self.logger.info(f"Testing connection to {self.provider_type} with config: {safe_config}")
    
    def log_model_discovery(self, model_count: int):
        """Log model discovery results"""
        self.logger.info(f"Discovered {model_count} models from {self.provider_type}")
    
    def extract_base_url(self, config: Dict[str, Any]) -> str:
        """
        Extract and format base URL from config
        
        Args:
            config: Provider configuration
            
        Returns:
            Formatted base URL
        """
        base_url = config.get('base_url', '').strip()
        port_no = config.get('port_no')
        
        if not base_url:
            return ''
        
        # Remove trailing slash
        base_url = base_url.rstrip('/')
        
        # Add port if specified and not already in URL
        if port_no and ':' not in base_url.split('//')[-1]:
            base_url = f"{base_url}:{port_no}"
        
        return base_url
    
    def make_request_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """
        Create request headers for API calls
        
        Args:
            config: Provider configuration
            
        Returns:
            Dictionary of HTTP headers
        """
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'DocumentEvaluator-LLMProvider/1.0'
        }
        
        # Add authorization header if API key is provided
        api_key = config.get('api_key')
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        return headers
    
    def parse_model_response(self, response_data: Any) -> List[Dict[str, Any]]:
        """
        Parse model list response from provider API
        
        Args:
            response_data: Raw response data from provider
            
        Returns:
            List of standardized model dictionaries
        """
        # Default implementation - should be overridden by specific providers
        if isinstance(response_data, list):
            return [{'model_name': str(item), 'model_id': str(item)} for item in response_data]
        elif isinstance(response_data, dict) and 'models' in response_data:
            return [{'model_name': str(item), 'model_id': str(item)} for item in response_data['models']]
        else:
            return []
    
    def get_health_check_endpoint(self, base_url: str) -> str:
        """
        Get health check endpoint for the provider
        
        Args:
            base_url: Provider base URL
            
        Returns:
            Health check endpoint URL
        """
        # Default implementation - can be overridden
        return f"{base_url}/health"
    
    def get_models_endpoint(self, base_url: str) -> str:
        """
        Get models list endpoint for the provider
        
        Args:
            base_url: Provider base URL
            
        Returns:
            Models endpoint URL
        """
        # Default implementation - should be overridden
        return f"{base_url}/models"
