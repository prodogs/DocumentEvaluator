"""
OpenAI Provider Adapter

Handles communication with OpenAI API for model discovery and connection testing.
"""

import requests
import json
from typing import Dict, Any, List, Tuple
from .base_provider import BaseLLMProvider

class OpenAIProvider(BaseLLMProvider):
    """OpenAI provider adapter"""
    
    def __init__(self):
        super().__init__('openai')
        self.default_base_url = 'https://api.openai.com/v1'
        self.timeout = 30  # seconds
    
    def test_connection(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Test connection to OpenAI API"""
        self.log_connection_attempt(config)
        
        try:
            api_key = config.get('api_key', '').strip()
            if not api_key:
                return False, "API key is required for OpenAI"
            
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
            return False, "Could not connect to OpenAI API"
        except requests.exceptions.Timeout:
            return False, f"Connection timeout after {self.timeout} seconds"
        except Exception as e:
            return False, self.format_error_message(e)
    
    def discover_models(self, config: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]], str]:
        """Discover available models from OpenAI"""
        try:
            api_key = config.get('api_key', '').strip()
            if not api_key:
                return False, [], "API key is required for OpenAI"
            
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
                        
                        # Add known model capabilities for common models
                        if 'gpt-4' in model_id:
                            capabilities['context_length'] = 8192
                            capabilities['type'] = 'chat'
                        elif 'gpt-3.5' in model_id:
                            capabilities['context_length'] = 4096
                            capabilities['type'] = 'chat'
                        elif 'text-embedding' in model_id:
                            capabilities['type'] = 'embedding'
                        elif 'whisper' in model_id:
                            capabilities['type'] = 'audio'
                        elif 'dall-e' in model_id:
                            capabilities['type'] = 'image'
                        
                        models.append({
                            'model_name': model_id,
                            'model_id': model_id,
                            'capabilities': capabilities
                        })
            
            self.log_model_discovery(len(models))
            return True, models, ""
            
        except requests.exceptions.ConnectionError:
            return False, [], "Could not connect to OpenAI API"
        except requests.exceptions.Timeout:
            return False, [], f"Request timeout after {self.timeout} seconds"
        except json.JSONDecodeError:
            return False, [], "Invalid JSON response from OpenAI"
        except Exception as e:
            return False, [], self.format_error_message(e)
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate OpenAI configuration"""
        api_key = config.get('api_key', '').strip()
        
        if not api_key:
            return False, "API key is required for OpenAI"
        
        # Basic API key format validation
        if not api_key.startswith('sk-'):
            return False, "OpenAI API key should start with 'sk-'"
        
        if len(api_key) < 20:
            return False, "OpenAI API key appears to be too short"
        
        # Base URL validation (optional)
        base_url = config.get('base_url', '').strip()
        if base_url:
            if not (base_url.startswith('http://') or base_url.startswith('https://')):
                return False, "Base URL must start with http:// or https://"
        
        return True, ""
    
    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for OpenAI"""
        return {
            'provider_type': 'openai',
            'base_url': self.default_base_url,
            'api_key': '',
            'port_no': None
        }
    
    def get_models_endpoint(self, base_url: str) -> str:
        """Get OpenAI models endpoint"""
        return f"{base_url}/models"
    
    def make_request_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Create request headers for OpenAI API calls"""
        headers = {
            'Content-Type': 'application/json',
            'User-Agent': 'DocumentEvaluator-LLMProvider/1.0'
        }
        
        api_key = config.get('api_key')
        if api_key:
            headers['Authorization'] = f'Bearer {api_key}'
        
        return headers
    
    def parse_model_response(self, response_data: Any) -> List[Dict[str, Any]]:
        """Parse OpenAI model list response"""
        models = []
        
        if isinstance(response_data, dict) and 'data' in response_data:
            for model_info in response_data['data']:
                model_id = model_info.get('id', '')
                if model_id:
                    capabilities = {}
                    
                    # Extract OpenAI-specific model information
                    for field in ['created', 'owned_by', 'object', 'permission']:
                        if field in model_info:
                            capabilities[field] = model_info[field]
                    
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
    
    def filter_chat_models(self, models: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """Filter models to only include chat/completion models"""
        chat_models = []
        chat_keywords = ['gpt-3.5', 'gpt-4', 'text-davinci', 'text-curie', 'text-babbage', 'text-ada']
        
        for model in models:
            model_name = model['model_name'].lower()
            if any(keyword in model_name for keyword in chat_keywords):
                # Skip embedding, audio, and image models
                if not any(skip in model_name for skip in ['embedding', 'whisper', 'dall-e', 'tts']):
                    chat_models.append(model)
        
        return chat_models
