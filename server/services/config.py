import os
import logging
from typing import Dict, Optional, Any
from dataclasses import dataclass
from enum import Enum

logger = logging.getLogger(__name__)

@dataclass
class DocumentProcessingConfig:
    """Configuration for document processing limits and settings"""
    max_file_size_mb: float = 50.0  # Maximum file size in MB
    min_file_size_bytes: int = 1     # Minimum file size in bytes

    @property
    def max_file_size_bytes(self) -> int:
        """Get maximum file size in bytes"""
        return int(self.max_file_size_mb * 1024 * 1024)

    @property
    def max_file_size_display(self) -> str:
        """Get human-readable file size limit"""
        if self.max_file_size_mb >= 1024:
            return f"{self.max_file_size_mb / 1024:.1f}GB"
        else:
            return f"{self.max_file_size_mb:.1f}MB"

class ServiceType(Enum):
    """Types of external services"""
    RAG_API = "rag_api"
    LLM_PROVIDER = "llm_provider"
    DOCUMENT_PROCESSOR = "document_processor"
    NOTIFICATION = "notification"

@dataclass
class ServiceConfig:
    """Configuration for an external service"""
    name: str
    service_type: ServiceType
    base_url: str
    port: Optional[int] = None
    api_key: Optional[str] = None
    timeout: int = 30
    max_retries: int = 3
    retry_delay: float = 1.0
    health_check_endpoint: Optional[str] = None
    enabled: bool = True
    
    @property
    def full_url(self) -> str:
        """Get the full URL for the service"""
        if self.port:
            return f"{self.base_url}:{self.port}"
        return self.base_url
    
    @property
    def health_check_url(self) -> str:
        """Get the health check URL for the service"""
        if self.health_check_endpoint:
            return f"{self.full_url}{self.health_check_endpoint}"
        return f"{self.full_url}/health"

class ServiceConfigManager:
    """Manages configuration for all external services"""

    def __init__(self):
        self.services: Dict[str, ServiceConfig] = {}
        self.document_config = DocumentProcessingConfig()
        self._load_default_configs()
        self._load_environment_configs()
        self._load_document_processing_config()
    
    def _load_default_configs(self):
        """Load default service configurations"""
        # RAG API Service (port 7001) - DISABLED until service is available
        self.services["rag_api"] = ServiceConfig(
            name="rag_api",
            service_type=ServiceType.RAG_API,
            base_url="http://localhost",
            port=7001,
            timeout=60,
            max_retries=3,
            retry_delay=2.0,
            health_check_endpoint="/api/health",
            enabled=False  # Disabled to prevent health check warnings
        )
        
        # Document Processor Service (current service - port 5001)
        self.services["document_processor"] = ServiceConfig(
            name="document_processor",
            service_type=ServiceType.DOCUMENT_PROCESSOR,
            base_url="http://localhost",
            port=5001,
            timeout=30,
            max_retries=2,
            retry_delay=1.0,
            health_check_endpoint="/api/health",
            enabled=True
        )
        
        logger.info("Default service configurations loaded")
    
    def _load_environment_configs(self):
        """Load service configurations from environment variables"""
        # RAG API configuration
        if os.getenv("RAG_API_URL"):
            rag_config = self.services["rag_api"]
            rag_config.base_url = os.getenv("RAG_API_URL", rag_config.base_url)
            rag_config.port = int(os.getenv("RAG_API_PORT", rag_config.port or 7001))
            rag_config.api_key = os.getenv("RAG_API_KEY")
            rag_config.timeout = int(os.getenv("RAG_API_TIMEOUT", rag_config.timeout))
            rag_config.enabled = os.getenv("RAG_API_ENABLED", "true").lower() == "true"
        
        # Document Processor configuration
        if os.getenv("DOC_PROCESSOR_URL"):
            doc_config = self.services["document_processor"]
            doc_config.base_url = os.getenv("DOC_PROCESSOR_URL", doc_config.base_url)
            doc_config.port = int(os.getenv("DOC_PROCESSOR_PORT", doc_config.port or 5001))
            doc_config.timeout = int(os.getenv("DOC_PROCESSOR_TIMEOUT", doc_config.timeout))
        
        logger.info("Environment service configurations loaded")

    def _load_document_processing_config(self):
        """Load document processing configuration from environment variables"""
        # Load max file size from environment (in MB)
        max_file_size_mb = float(os.getenv("MAX_FILE_SIZE_MB", self.document_config.max_file_size_mb))
        min_file_size_bytes = int(os.getenv("MIN_FILE_SIZE_BYTES", self.document_config.min_file_size_bytes))

        self.document_config.max_file_size_mb = max_file_size_mb
        self.document_config.min_file_size_bytes = min_file_size_bytes

        logger.info(f"Document processing config loaded: max_file_size={self.document_config.max_file_size_display}, min_file_size={min_file_size_bytes} bytes")

    def get_service(self, service_name: str) -> Optional[ServiceConfig]:
        """Get configuration for a specific service"""
        return self.services.get(service_name)

    def get_document_config(self) -> DocumentProcessingConfig:
        """Get document processing configuration"""
        return self.document_config
    
    def get_services_by_type(self, service_type: ServiceType) -> Dict[str, ServiceConfig]:
        """Get all services of a specific type"""
        return {
            name: config for name, config in self.services.items()
            if config.service_type == service_type
        }
    
    def add_service(self, service_config: ServiceConfig):
        """Add a new service configuration"""
        self.services[service_config.name] = service_config
        logger.info(f"Added service configuration: {service_config.name}")
    
    def update_service(self, service_name: str, **kwargs):
        """Update an existing service configuration"""
        if service_name in self.services:
            config = self.services[service_name]
            for key, value in kwargs.items():
                if hasattr(config, key):
                    setattr(config, key, value)
            logger.info(f"Updated service configuration: {service_name}")
        else:
            logger.warning(f"Service not found: {service_name}")
    
    def disable_service(self, service_name: str):
        """Disable a service"""
        if service_name in self.services:
            self.services[service_name].enabled = False
            logger.info(f"Disabled service: {service_name}")
    
    def enable_service(self, service_name: str):
        """Enable a service"""
        if service_name in self.services:
            self.services[service_name].enabled = True
            logger.info(f"Enabled service: {service_name}")
    
    def get_enabled_services(self) -> Dict[str, ServiceConfig]:
        """Get all enabled services"""
        return {
            name: config for name, config in self.services.items()
            if config.enabled
        }
    
    def list_services(self) -> Dict[str, Dict[str, Any]]:
        """List all services with their configurations"""
        return {
            name: {
                "name": config.name,
                "type": config.service_type.value,
                "url": config.full_url,
                "enabled": config.enabled,
                "timeout": config.timeout,
                "max_retries": config.max_retries
            }
            for name, config in self.services.items()
        }

# Global configuration instance
config_manager = ServiceConfigManager()

# Backward compatibility alias
service_config = config_manager
