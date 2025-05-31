"""
LM Studio Provider Adapter

Handles communication with LM Studio local server for model discovery and connection testing.
LM Studio provides an OpenAI-compatible API.
"""

import requests
import json
from typing import Dict, Any, List, Tuple
from .base_provider import BaseLLMProvider

class LMStudioProvider(BaseLLMProvider):
    """LM Studio provider adapter"""
    
    def __init__(self):
        super().__init__('lmstudio')
        self.default_port = 1234
        self.timeout = 15  # seconds
    
    def test_connection(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Test connection to LM Studio server"""
        self.log_connection_attempt(config)
        
        try:
            base_url = self.extract_base_url(config)
            if not base_url:
                return False, "Base URL is required for LM Studio"
            
            # LM Studio uses OpenAI-compatible API
            models_url = f"{base_url}/v1/models"
            
            response = requests.get(
                models_url,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return True, "Connection successful"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except requests.exceptions.ConnectionError:
            return False, "Could not connect to LM Studio server. Is it running?"
        except requests.exceptions.Timeout:
            return False, f"Connection timeout after {self.timeout} seconds"
        except Exception as e:
            return False, self.format_error_message(e)
    
    def discover_models(self, config: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]], str]:
        """Discover available models from LM Studio"""
        try:
            base_url = self.extract_base_url(config)
            if not base_url:
                return False, [], "Base URL is required for LM Studio"
            
            # LM Studio models endpoint (OpenAI-compatible)
            models_url = f"{base_url}/v1/models"
            
            response = requests.get(
                models_url,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code != 200:
                return False, [], f"HTTP {response.status_code}: {response.text}"
            
            data = response.json()
            models = []
            
            if 'data' in data:
                for model_info in data['data']:
                    model_id = model_info.get('id', '')
                    if model_id:
                        # Extract model capabilities
                        capabilities = {}
                        if 'created' in model_info:
                            capabilities['created'] = model_info['created']
                        if 'owned_by' in model_info:
                            capabilities['owned_by'] = model_info['owned_by']
                        if 'object' in model_info:
                            capabilities['object'] = model_info['object']
                        
                        # LM Studio specific capabilities
                        capabilities['provider'] = 'lmstudio'
                        capabilities['type'] = 'chat'  # LM Studio primarily serves chat models
                        
                        models.append({
                            'model_name': model_id,
                            'model_id': model_id,
                            'capabilities': capabilities
                        })
            
            self.log_model_discovery(len(models))
            return True, models, ""
            
        except requests.exceptions.ConnectionError:
            return False, [], "Could not connect to LM Studio server"
        except requests.exceptions.Timeout:
            return False, [], f"Request timeout after {self.timeout} seconds"
        except json.JSONDecodeError:
            return False, [], "Invalid JSON response from LM Studio"
        except Exception as e:
            return False, [], self.format_error_message(e)
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate LM Studio configuration"""
        base_url = config.get('base_url', '').strip()
        
        if not base_url:
            return False, "Base URL is required for LM Studio"
        
        # Check if URL format is valid
        if not (base_url.startswith('http://') or base_url.startswith('https://')):
            return False, "Base URL must start with http:// or https://"
        
        # Port validation
        port_no = config.get('port_no')
        if port_no is not None:
            try:
                port = int(port_no)
                if port < 1 or port > 65535:
                    return False, "Port number must be between 1 and 65535"
            except (ValueError, TypeError):
                return False, "Port number must be a valid integer"
        
        return True, ""
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for LM Studio"""
        return {
            'provider_type': 'lmstudio',
            'base_url': 'http://localhost:1234',
            'api_key': '',  # LM Studio doesn't require API key by default
            'port_no': self.default_port
        }
    
    def get_models_endpoint(self, base_url: str) -> str:
        """Get LM Studio models endpoint"""
        return f"{base_url}/v1/models"
    
    def get_health_check_endpoint(self, base_url: str) -> str:
        """Get LM Studio health check endpoint"""
        return f"{base_url}/v1/models"
    
    def make_request_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Create request headers for LM Studio API calls"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'DocumentEvaluator-LLMProvider/1.0'
        }
        
        # LM Studio may optionally use API keys
        api_key = config.get('api_key')
        if api_key and api_key.strip():
            headers['Authorization'] = f'Bearer {api_key}'
        
        return headers
    
    def parse_model_response(self, response_data: Any) -> List[Dict[str, Any]]:
        """Parse LM Studio model list response (OpenAI-compatible format)"""
        models = []
        
        if isinstance(response_data, dict) and 'data' in response_data:
            for model_info in response_data['data']:
                model_id = model_info.get('id', '')
                if model_id:
                    capabilities = {}
                    
                    # Extract model information
                    for field in ['created', 'owned_by', 'object']:
                        if field in model_info:
                            capabilities[field] = model_info[field]
                    
                    # Add LM Studio specific info
                    capabilities['provider'] = 'lmstudio'
                    capabilities['type'] = 'chat'
                    
                    models.append({
                        'model_name': model_id,
                        'model_id': model_id,
                        'capabilities': capabilities
                    })
        
        return models
    
    def get_server_info(self, config: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], str]:
        """Get LM Studio server information"""
        try:
            base_url = self.extract_base_url(config)
            if not base_url:
                return False, {}, "Base URL is required"
            
            # Try to get server info (if available)
            info_url = f"{base_url}/v1/models"
            headers = self.make_request_headers(config)
            
            response = requests.get(
                info_url,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                data = response.json()
                server_info = {
                    'status': 'running',
                    'model_count': len(data.get('data', [])),
                    'api_version': 'v1',
                    'compatible_with': 'OpenAI API'
                }
                return True, server_info, ""
            else:
                return False, {}, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, {}, self.format_error_message(e)
    
    def test_chat_completion(self, config: Dict[str, Any], model_name: str) -> Tuple[bool, str]:
        """Test chat completion with a specific model"""
        try:
            base_url = self.extract_base_url(config)
            if not base_url:
                return False, "Base URL is required"
            
            chat_url = f"{base_url}/v1/chat/completions"
            headers = self.make_request_headers(config)
            
            payload = {
                "model": model_name,
                "messages": [{"role": "user", "content": "Hello, this is a test message."}],
                "max_tokens": 10,
                "temperature": 0.1
            }
            
            response = requests.post(
                chat_url,
                json=payload,
                headers=headers,
                timeout=30  # Longer timeout for inference
            )
            
            if response.status_code == 200:
                return True, "Chat completion test successful"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, self.format_error_message(e)
