"""
Grok Provider Adapter

Handles communication with Grok (X.AI) API for model discovery and connection testing.
Grok uses an OpenAI-compatible API format.
"""

import requests
import json
from typing import Dict, Any, List, Tuple
from .base_provider import BaseLLMProvider

class GrokProvider(BaseLLMProvider):
    """Grok (X.AI) provider adapter"""
    
    def __init__(self):
        super().__init__('grok')
        self.default_base_url = 'https://api.x.ai/v1'
        self.timeout = 30  # seconds
        
        # Known Grok models
        self.known_models = [
            {
                'model_name': 'Grok Beta',
                'model_id': 'grok-beta',
                'capabilities': {
                    'provider': 'X.AI',
                    'type': 'chat',
                    'context_length': 131072,  # 128k context
                    'real_time_info': True
                }
            },
            {
                'model_name': 'Grok Vision Beta',
                'model_id': 'grok-vision-beta',
                'capabilities': {
                    'provider': 'X.AI',
                    'type': 'chat',
                    'context_length': 131072,
                    'multimodal': True,
                    'real_time_info': True
                }
            }
        ]
    
    def test_connection(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Test connection to Grok API"""
        self.log_connection_attempt(config)
        
        try:
            api_key = config.get('api_key', '').strip()
            if not api_key:
                return False, "API key is required for Grok"
            
            base_url = self.extract_base_url(config) or self.default_base_url
            
            # Test with a simple models list request
            models_url = f"{base_url}/models"
            headers = self.make_request_headers(config)
            
            response = requests.get(
                models_url,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                return True, "Connection successful"
            elif response.status_code == 401:
                return False, "Invalid API key"
            elif response.status_code == 403:
                return False, "API key does not have required permissions"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except requests.exceptions.ConnectionError:
            return False, "Could not connect to Grok API"
        except requests.exceptions.Timeout:
            return False, f"Connection timeout after {self.timeout} seconds"
        except Exception as e:
            return False, self.format_error_message(e)
    
    def discover_models(self, config: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]], str]:
        """Discover available models from Grok"""
        try:
            api_key = config.get('api_key', '').strip()
            if not api_key:
                return False, [], "API key is required for Grok"
            
            base_url = self.extract_base_url(config) or self.default_base_url
            models_url = f"{base_url}/models"
            headers = self.make_request_headers(config)
            
            response = requests.get(
                models_url,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                if response.status_code == 401:
                    return False, [], "Invalid API key"
                elif response.status_code == 403:
                    return False, [], "API key does not have required permissions"
                else:
                    # If API call fails, return known models
                    self.log_model_discovery(len(self.known_models))
                    return True, self.known_models.copy(), "Using known models (API unavailable)"
            
            try:
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
                            
                            # Add Grok-specific capabilities
                            capabilities['provider'] = 'X.AI'
                            capabilities['type'] = 'chat'
                            if 'grok' in model_id.lower():
                                capabilities['real_time_info'] = True
                                capabilities['context_length'] = 131072
                            if 'vision' in model_id.lower():
                                capabilities['multimodal'] = True
                            
                            models.append({
                                'model_name': model_id,
                                'model_id': model_id,
                                'capabilities': capabilities
                            })
                
                # If no models returned from API, use known models
                if not models:
                    models = self.known_models.copy()
                
                self.log_model_discovery(len(models))
                return True, models, ""
                
            except json.JSONDecodeError:
                # If JSON parsing fails, return known models
                self.log_model_discovery(len(self.known_models))
                return True, self.known_models.copy(), "Using known models (invalid API response)"
            
        except requests.exceptions.ConnectionError:
            # If connection fails, return known models
            self.log_model_discovery(len(self.known_models))
            return True, self.known_models.copy(), "Using known models (connection failed)"
        except requests.exceptions.Timeout:
            return False, [], f"Request timeout after {self.timeout} seconds"
        except Exception as e:
            return False, [], self.format_error_message(e)
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate Grok configuration"""
        api_key = config.get('api_key', '').strip()
        
        if not api_key:
            return False, "API key is required for Grok"
        
        # Basic API key format validation for Grok
        if len(api_key) < 20:
            return False, "Grok API key appears to be too short"
        
        # Base URL validation (optional)
        base_url = config.get('base_url', '').strip()
        if base_url:
            if not (base_url.startswith('http://') or base_url.startswith('https://')):
                return False, "Base URL must start with http:// or https://"
        
        return True, ""
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for Grok"""
        return {
            'provider_type': 'grok',
            'base_url': self.default_base_url,
            'api_key': '',
            'port_no': None
        }
    
    def get_models_endpoint(self, base_url: str) -> str:
        """Get Grok models endpoint"""
        return f"{base_url}/models"
    
    def make_request_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Create request headers for Grok API calls"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'DocumentEvaluator-LLMProvider/1.0'
        }
        
        api_key = config.get('api_key')
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        return headers
    
    def parse_model_response(self, response_data: Any) -> List[Dict[str, Any]]:
        """Parse Grok model list response"""
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
                    
                    # Add Grok-specific capabilities
                    capabilities['provider'] = 'X.AI'
                    capabilities['type'] = 'chat'
                    if 'grok' in model_id.lower():
                        capabilities['real_time_info'] = True
                        capabilities['context_length'] = 131072
                    if 'vision' in model_id.lower():
                        capabilities['multimodal'] = True
                    
                    models.append({
                        'model_name': model_id,
                        'model_id': model_id,
                        'capabilities': capabilities
                    })
        
        return models
    
    def get_model_info(self, config: Dict[str, Any], model_id: str) -> Tuple[bool, Dict[str, Any], str]:
        """Get detailed information about a specific model"""
        try:
            api_key = config.get('api_key', '').strip()
            if not api_key:
                return False, {}, "API key is required"
            
            base_url = self.extract_base_url(config) or self.default_base_url
            model_url = f"{base_url}/models/{model_id}"
            headers = self.make_request_headers(config)
            
            response = requests.get(
                model_url,
                headers=headers,
                timeout=self.timeout
            )
            
            if response.status_code == 200:
                model_info = response.json()
                return True, model_info, ""
            elif response.status_code == 404:
                return False, {}, f"Model '{model_id}' not found"
            else:
                return False, {}, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, {}, self.format_error_message(e)
    
    def test_chat_completion(self, config: Dict[str, Any], model_name: str) -> Tuple[bool, str]:
        """Test chat completion with a specific model"""
        try:
            api_key = config.get('api_key', '').strip()
            if not api_key:
                return False, "API key is required"
            
            base_url = self.extract_base_url(config) or self.default_base_url
            chat_url = f"{base_url}/chat/completions"
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
