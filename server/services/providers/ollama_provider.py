"""
Ollama Provider Adapter

Handles communication with Ollama LLM service for model discovery and connection testing.
"""

import requests
import json
from typing import Dict, Any, List, Tuple
from .base_provider import BaseLLMProvider

class OllamaProvider(BaseLLMProvider):
    """Ollama provider adapter"""
    
    def __init__(self):
        super().__init__('ollama')
        self.default_port = 11434
        self.timeout = 10  # seconds
    
    def test_connection(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Test connection to Ollama service"""
        self.log_connection_attempt(config)
        
        try:
            base_url = self.extract_base_url(config)
            if not base_url:
                return False, "Base URL is required for Ollama"
            
            # Ollama health check endpoint
            health_url = f"{base_url}/api/tags"
            
            response = requests.get(
                health_url,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code == 200:
                return True, "Connection successful"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except requests.exceptions.ConnectionError:
            return False, "Could not connect to Ollama service. Is it running?"
        except requests.exceptions.Timeout:
            return False, f"Connection timeout after {self.timeout} seconds"
        except Exception as e:
            return False, self.format_error_message(e)
    
    def discover_models(self, config: Dict[str, Any]) -> Tuple[bool, List[Dict[str, Any]], str]:
        """Discover available models from Ollama"""
        try:
            base_url = self.extract_base_url(config)
            if not base_url:
                return False, [], "Base URL is required for Ollama"
            
            # Ollama models endpoint
            models_url = f"{base_url}/api/tags"
            
            response = requests.get(
                models_url,
                timeout=self.timeout,
                headers={'Content-Type': 'application/json'}
            )
            
            if response.status_code != 200:
                return False, [], f"HTTP {response.status_code}: {response.text}"
            
            data = response.json()
            models = []
            
            if 'models' in data:
                for model_info in data['models']:
                    model_name = model_info.get('name', '')
                    if model_name:
                        # Extract model capabilities if available
                        capabilities = {}
                        if 'size' in model_info:
                            capabilities['size'] = model_info['size']
                        if 'modified_at' in model_info:
                            capabilities['modified_at'] = model_info['modified_at']
                        if 'digest' in model_info:
                            capabilities['digest'] = model_info['digest']
                        
                        models.append({
                            'model_name': model_name,
                            'model_id': model_name,  # Ollama uses name as ID
                            'capabilities': capabilities
                        })
            
            self.log_model_discovery(len(models))
            return True, models, ""
            
        except requests.exceptions.ConnectionError:
            return False, [], "Could not connect to Ollama service"
        except requests.exceptions.Timeout:
            return False, [], f"Request timeout after {self.timeout} seconds"
        except json.JSONDecodeError:
            return False, [], "Invalid JSON response from Ollama"
        except Exception as e:
            return False, [], self.format_error_message(e)
    
    def validate_config(self, config: Dict[str, Any]) -> Tuple[bool, str]:
        """Validate Ollama configuration"""
        base_url = config.get('base_url', '').strip()
        
        if not base_url:
            return False, "Base URL is required for Ollama"
        
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
        """Get default configuration for Ollama"""
        return {
            'provider_type': 'ollama',
            'base_url': 'http://localhost:11434',
            'api_key': '',  # Ollama doesn't require API key
            'port_no': self.default_port
        }
    
    def get_models_endpoint(self, base_url: str) -> str:
        """Get Ollama models endpoint"""
        return f"{base_url}/api/tags"
    
    def get_health_check_endpoint(self, base_url: str) -> str:
        """Get Ollama health check endpoint"""
        return f"{base_url}/api/tags"
    
    def make_request_headers(self, config: Dict[str, Any]) -> Dict[str, str]:
        """Create request headers for Ollama API calls"""
        # Ollama doesn't require authorization headers
        return {
            'Content-Type': 'application/json',
            'User-Agent': 'DocumentEvaluator-LLMProvider/1.0'
        }
    
    def parse_model_response(self, response_data: Any) -> List[Dict[str, Any]]:
        """Parse Ollama model list response"""
        models = []
        
        if isinstance(response_data, dict) and 'models' in response_data:
            for model_info in response_data['models']:
                model_name = model_info.get('name', '')
                if model_name:
                    capabilities = {}
                    
                    # Extract Ollama-specific model information
                    for field in ['size', 'modified_at', 'digest', 'details']:
                        if field in model_info:
                            capabilities[field] = model_info[field]
                    
                    models.append({
                        'model_name': model_name,
                        'model_id': model_name,
                        'capabilities': capabilities
                    })
        
        return models
    
    def get_model_info(self, config: Dict[str, Any], model_name: str) -> Tuple[bool, Dict[str, Any], str]:
        """Get detailed information about a specific model"""
        try:
            base_url = self.extract_base_url(config)
            if not base_url:
                return False, {}, "Base URL is required"
            
            # Ollama model show endpoint
            show_url = f"{base_url}/api/show"
            payload = {'name': model_name}
            
            response = requests.post(
                show_url,
                json=payload,
                timeout=self.timeout,
                headers=self.make_request_headers(config)
            )
            
            if response.status_code == 200:
                model_info = response.json()
                return True, model_info, ""
            else:
                return False, {}, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, {}, self.format_error_message(e)
    
    def pull_model(self, config: Dict[str, Any], model_name: str) -> Tuple[bool, str]:
        """Pull/download a model to Ollama"""
        try:
            base_url = self.extract_base_url(config)
            if not base_url:
                return False, "Base URL is required"
            
            # Ollama pull endpoint
            pull_url = f"{base_url}/api/pull"
            payload = {'name': model_name}
            
            response = requests.post(
                pull_url,
                json=payload,
                timeout=300,  # Longer timeout for model downloads
                headers=self.make_request_headers(config)
            )
            
            if response.status_code == 200:
                return True, f"Model {model_name} pulled successfully"
            else:
                return False, f"HTTP {response.status_code}: {response.text}"
                
        except Exception as e:
            return False, self.format_error_message(e)
