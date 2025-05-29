import time
import requests
import logging
from typing import Dict, Optional, Any, Union
from dataclasses import dataclass
from enum import Enum

from server.services.config import service_config, ServiceConfig
from server.services.health_monitor import health_monitor

logger = logging.getLogger(__name__)

class RequestMethod(Enum):
    """HTTP request methods"""
    GET = "GET"
    POST = "POST"
    PUT = "PUT"
    DELETE = "DELETE"
    PATCH = "PATCH"

@dataclass
class ServiceResponse:
    """Response from a service call"""
    success: bool
    status_code: Optional[int]
    data: Optional[Dict] = None
    error_message: Optional[str] = None
    response_time_ms: float = 0
    retry_count: int = 0

class ServiceClient:
    """Client for making requests to external services with retry logic and circuit breaker"""
    
    def __init__(self):
        self.session = requests.Session()
        # Set default headers
        self.session.headers.update({
            "User-Agent": "DocumentEvaluator-ServiceClient/1.0",
            "Accept": "application/json"
        })
    
    def call_service(
        self,
        service_name: str,
        endpoint: str,
        method: RequestMethod = RequestMethod.GET,
        data: Optional[Dict] = None,
        files: Optional[Dict] = None,
        params: Optional[Dict] = None,
        headers: Optional[Dict] = None,
        timeout: Optional[int] = None,
        retry_override: Optional[int] = None
    ) -> ServiceResponse:
        """
        Make a request to an external service with retry logic
        
        Args:
            service_name: Name of the service to call
            endpoint: API endpoint (e.g., "/analyze_document")
            method: HTTP method
            data: Request data (for POST/PUT requests)
            files: Files to upload
            params: Query parameters
            headers: Additional headers
            timeout: Request timeout override
            retry_override: Override max retries for this request
            
        Returns:
            ServiceResponse with the result
        """
        config = service_config.get_service(service_name)
        if not config:
            return ServiceResponse(
                success=False,
                status_code=None,
                error_message=f"Service configuration not found: {service_name}"
            )
        
        if not config.enabled:
            return ServiceResponse(
                success=False,
                status_code=None,
                error_message=f"Service is disabled: {service_name}"
            )
        
        # Check if service is healthy before making request
        if not health_monitor.is_service_healthy(service_name):
            logger.warning(f"Service {service_name} is not healthy, attempting request anyway")
        
        # Build full URL
        url = f"{config.full_url}{endpoint}"
        
        # Prepare request parameters
        request_timeout = timeout or config.timeout
        max_retries = retry_override if retry_override is not None else config.max_retries
        
        # Prepare headers
        request_headers = {}
        if config.api_key:
            request_headers["Authorization"] = f"Bearer {config.api_key}"
        if headers:
            request_headers.update(headers)
        
        # Attempt request with retries
        last_error = None
        for attempt in range(max_retries + 1):
            start_time = time.time()
            
            try:
                logger.debug(f"Attempting {method.value} request to {url} (attempt {attempt + 1}/{max_retries + 1})")
                
                response = self.session.request(
                    method=method.value,
                    url=url,
                    json=data if data and not files else None,
                    data=data if data and files else None,
                    files=files,
                    params=params,
                    headers=request_headers,
                    timeout=request_timeout
                )
                
                response_time_ms = (time.time() - start_time) * 1000
                
                # Check if request was successful
                if response.status_code < 400:
                    # Try to parse JSON response
                    try:
                        response_data = response.json() if response.content else {}
                    except ValueError:
                        response_data = {"raw_response": response.text}
                    
                    logger.debug(f"Successful request to {service_name}: {response.status_code}")
                    return ServiceResponse(
                        success=True,
                        status_code=response.status_code,
                        data=response_data,
                        response_time_ms=response_time_ms,
                        retry_count=attempt
                    )
                else:
                    # Server error - might be worth retrying
                    error_msg = f"HTTP {response.status_code}: {response.text[:200]}"
                    logger.warning(f"Request to {service_name} failed: {error_msg}")
                    
                    if attempt < max_retries and self._should_retry(response.status_code):
                        self._wait_before_retry(config.retry_delay, attempt)
                        continue
                    else:
                        return ServiceResponse(
                            success=False,
                            status_code=response.status_code,
                            error_message=error_msg,
                            response_time_ms=response_time_ms,
                            retry_count=attempt
                        )
                        
            except requests.exceptions.Timeout as e:
                response_time_ms = (time.time() - start_time) * 1000
                last_error = f"Request timeout after {request_timeout}s"
                logger.warning(f"Timeout calling {service_name}: {last_error}")
                
            except requests.exceptions.ConnectionError as e:
                response_time_ms = (time.time() - start_time) * 1000
                last_error = f"Connection error: {str(e)}"
                logger.warning(f"Connection error calling {service_name}: {last_error}")
                
            except Exception as e:
                response_time_ms = (time.time() - start_time) * 1000
                last_error = f"Unexpected error: {str(e)}"
                logger.error(f"Unexpected error calling {service_name}: {last_error}", exc_info=True)
            
            # Wait before retry (except on last attempt)
            if attempt < max_retries:
                self._wait_before_retry(config.retry_delay, attempt)
        
        # All retries exhausted
        return ServiceResponse(
            success=False,
            status_code=None,
            error_message=last_error or "All retry attempts failed",
            response_time_ms=response_time_ms,
            retry_count=max_retries
        )
    
    def _should_retry(self, status_code: int) -> bool:
        """Determine if a request should be retried based on status code"""
        # Retry on server errors and some client errors
        retry_codes = {
            408,  # Request Timeout
            429,  # Too Many Requests
            500,  # Internal Server Error
            502,  # Bad Gateway
            503,  # Service Unavailable
            504,  # Gateway Timeout
        }
        return status_code in retry_codes
    
    def _wait_before_retry(self, base_delay: float, attempt: int):
        """Wait before retrying with exponential backoff"""
        # Exponential backoff: base_delay * (2 ^ attempt)
        delay = base_delay * (2 ** attempt)
        # Add some jitter to avoid thundering herd
        jitter = delay * 0.1 * (time.time() % 1)  # 0-10% jitter
        total_delay = delay + jitter
        
        logger.debug(f"Waiting {total_delay:.2f}s before retry")
        time.sleep(total_delay)
    
    def get_service_info(self, service_name: str) -> Optional[Dict]:
        """Get information about a service"""
        config = service_config.get_service(service_name)
        if not config:
            return None
            
        return {
            "name": config.name,
            "type": config.service_type.value,
            "url": config.full_url,
            "enabled": config.enabled,
            "timeout": config.timeout,
            "max_retries": config.max_retries,
            "health_status": health_monitor.get_service_status(service_name).value if health_monitor.get_service_status(service_name) else "unknown"
        }
    
    def list_services(self) -> Dict[str, Dict]:
        """List all configured services"""
        return {
            name: self.get_service_info(name)
            for name in service_config.services.keys()
        }

# Convenience methods for common service calls
class RAGServiceClient:
    """Specialized client for RAG API service"""
    
    def __init__(self):
        self.client = ServiceClient()
        self.service_name = "rag_api"
    
    def analyze_document(self, file_data: bytes, filename: str, prompts: list, llm_provider: str) -> ServiceResponse:
        """Analyze a document using the RAG service"""
        files = {
            'file': (filename, file_data, self._get_mime_type(filename))
        }
        
        data = {
            'prompts': str(prompts),  # Convert to string as expected by service
            'llm_provider': llm_provider
        }
        
        return self.client.call_service(
            service_name=self.service_name,
            endpoint="/analyze_document_with_llm",
            method=RequestMethod.POST,
            data=data,
            files=files,
            timeout=60  # Longer timeout for document analysis
        )
    
    def get_analysis_status(self, task_id: str) -> ServiceResponse:
        """Get the status of a document analysis task"""
        return self.client.call_service(
            service_name=self.service_name,
            endpoint=f"/analyze_status/{task_id}",
            method=RequestMethod.GET,
            timeout=30
        )
    
    def _get_mime_type(self, filename: str) -> str:
        """Get MIME type based on file extension"""
        extension = filename.lower().split('.')[-1] if '.' in filename else ''
        mime_types = {
            'pdf': 'application/pdf',
            'txt': 'text/plain',
            'md': 'text/markdown',
            'doc': 'application/msword',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'xls': 'application/vnd.ms-excel',
            'xlsx': 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        }
        return mime_types.get(extension, 'application/octet-stream')

# Global service clients
service_client = ServiceClient()
rag_client = RAGServiceClient()
