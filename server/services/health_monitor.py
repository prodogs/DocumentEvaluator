import time
import threading
import requests
import logging
from datetime import datetime, timedelta
from typing import Dict, Optional, List
from enum import Enum
from dataclasses import dataclass, field

from server.services.config import service_config, ServiceConfig

logger = logging.getLogger(__name__)

class HealthStatus(Enum):
    """Health status of a service"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"
    DEGRADED = "degraded"

@dataclass
class HealthCheck:
    """Result of a health check"""
    service_name: str
    status: HealthStatus
    response_time_ms: float
    timestamp: datetime
    error_message: Optional[str] = None
    status_code: Optional[int] = None
    details: Dict = field(default_factory=dict)

class ServiceHealthMonitor:
    """Monitors the health of external services"""
    
    def __init__(self, check_interval: int = 30):
        """
        Initialize the health monitor
        
        Args:
            check_interval (int): Seconds between health checks (default: 30)
        """
        self.check_interval = check_interval
        self.health_checks: Dict[str, List[HealthCheck]] = {}
        self.current_status: Dict[str, HealthStatus] = {}
        self.monitoring_thread: Optional[threading.Thread] = None
        self.stop_monitoring = False
        self.max_history = 100  # Keep last 100 health checks per service
        
    def start_monitoring(self):
        """Start the health monitoring thread"""
        if self.monitoring_thread and self.monitoring_thread.is_alive():
            logger.warning("Health monitoring is already running")
            return
            
        self.stop_monitoring = False
        self.monitoring_thread = threading.Thread(target=self._monitoring_loop, daemon=True)
        self.monitoring_thread.start()
        logger.info("Service health monitoring started")
        
    def stop_monitoring_service(self):
        """Stop the health monitoring thread"""
        self.stop_monitoring = True
        if self.monitoring_thread:
            self.monitoring_thread.join(timeout=5)
        logger.info("Service health monitoring stopped")
        
    def _monitoring_loop(self):
        """Main monitoring loop"""
        while not self.stop_monitoring:
            try:
                self._check_all_services()
                time.sleep(self.check_interval)
            except Exception as e:
                logger.error(f"Error in health monitoring loop: {e}", exc_info=True)
                time.sleep(self.check_interval)
                
    def _check_all_services(self):
        """Check health of all enabled services"""
        enabled_services = service_config.get_enabled_services()
        
        for service_name, config in enabled_services.items():
            try:
                health_check = self._check_service_health(config)
                self._record_health_check(health_check)
            except Exception as e:
                logger.error(f"Error checking health of {service_name}: {e}")
                # Record failed health check
                failed_check = HealthCheck(
                    service_name=service_name,
                    status=HealthStatus.UNHEALTHY,
                    response_time_ms=0,
                    timestamp=datetime.utcnow(),
                    error_message=str(e)
                )
                self._record_health_check(failed_check)
                
    def _check_service_health(self, config: ServiceConfig) -> HealthCheck:
        """Check health of a specific service"""
        start_time = time.time()
        
        try:
            response = requests.get(
                config.health_check_url,
                timeout=config.timeout,
                headers=self._get_headers(config)
            )
            
            response_time_ms = (time.time() - start_time) * 1000
            
            # Determine health status based on response
            if response.status_code == 200:
                status = HealthStatus.HEALTHY
                error_message = None
            elif 200 <= response.status_code < 300:
                status = HealthStatus.HEALTHY
                error_message = None
            elif 500 <= response.status_code < 600:
                status = HealthStatus.UNHEALTHY
                error_message = f"Server error: {response.status_code}"
            else:
                status = HealthStatus.DEGRADED
                error_message = f"Unexpected status: {response.status_code}"
            
            # Try to parse response details
            details = {}
            try:
                if response.headers.get('content-type', '').startswith('application/json'):
                    details = response.json()
            except:
                details = {"raw_response": response.text[:200]}
            
            return HealthCheck(
                service_name=config.name,
                status=status,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                error_message=error_message,
                status_code=response.status_code,
                details=details
            )
            
        except requests.exceptions.Timeout:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                service_name=config.name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                error_message="Request timeout"
            )
            
        except requests.exceptions.ConnectionError:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                service_name=config.name,
                status=HealthStatus.UNHEALTHY,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                error_message="Connection error - service may be down"
            )
            
        except Exception as e:
            response_time_ms = (time.time() - start_time) * 1000
            return HealthCheck(
                service_name=config.name,
                status=HealthStatus.UNKNOWN,
                response_time_ms=response_time_ms,
                timestamp=datetime.utcnow(),
                error_message=f"Unexpected error: {str(e)}"
            )
    
    def _get_headers(self, config: ServiceConfig) -> Dict[str, str]:
        """Get headers for health check requests"""
        headers = {
            "User-Agent": "DocumentEvaluator-HealthMonitor/1.0",
            "Accept": "application/json"
        }
        
        if config.api_key:
            headers["Authorization"] = f"Bearer {config.api_key}"
            
        return headers
    
    def _record_health_check(self, health_check: HealthCheck):
        """Record a health check result"""
        service_name = health_check.service_name
        
        # Initialize history for new services
        if service_name not in self.health_checks:
            self.health_checks[service_name] = []
        
        # Add new health check
        self.health_checks[service_name].append(health_check)
        
        # Maintain history limit
        if len(self.health_checks[service_name]) > self.max_history:
            self.health_checks[service_name] = self.health_checks[service_name][-self.max_history:]
        
        # Update current status
        self.current_status[service_name] = health_check.status
        
        # Log status changes
        if len(self.health_checks[service_name]) > 1:
            previous_status = self.health_checks[service_name][-2].status
            if previous_status != health_check.status:
                logger.info(f"Service {service_name} status changed: {previous_status.value} -> {health_check.status.value}")
        
    def get_service_status(self, service_name: str) -> Optional[HealthStatus]:
        """Get current status of a service"""
        return self.current_status.get(service_name, HealthStatus.UNKNOWN)
    
    def get_service_health_history(self, service_name: str, limit: int = 10) -> List[HealthCheck]:
        """Get recent health check history for a service"""
        if service_name not in self.health_checks:
            return []
        return self.health_checks[service_name][-limit:]
    
    def get_all_service_status(self) -> Dict[str, Dict]:
        """Get status of all monitored services"""
        result = {}
        
        for service_name in service_config.services.keys():
            status = self.get_service_status(service_name)
            recent_checks = self.get_service_health_history(service_name, 3)
            
            # Calculate average response time from recent checks
            avg_response_time = 0
            if recent_checks:
                avg_response_time = sum(check.response_time_ms for check in recent_checks) / len(recent_checks)
            
            result[service_name] = {
                "status": status.value if status else "unknown",
                "last_check": recent_checks[-1].timestamp.isoformat() if recent_checks else None,
                "avg_response_time_ms": round(avg_response_time, 2),
                "recent_checks": len(recent_checks),
                "error_message": recent_checks[-1].error_message if recent_checks and recent_checks[-1].error_message else None
            }
            
        return result
    
    def is_service_healthy(self, service_name: str) -> bool:
        """Check if a service is currently healthy"""
        status = self.get_service_status(service_name)
        return status == HealthStatus.HEALTHY
    
    def check_service_now(self, service_name: str) -> Optional[HealthCheck]:
        """Perform an immediate health check for a specific service"""
        config = service_config.get_service(service_name)
        if not config:
            logger.warning(f"Service configuration not found: {service_name}")
            return None
            
        health_check = self._check_service_health(config)
        self._record_health_check(health_check)
        return health_check

# Global health monitor instance
health_monitor = ServiceHealthMonitor()
