"""
Example of how to integrate stability improvements into BatchService
This shows practical usage of the stability helpers
"""

from typing import Dict, Any, Optional
import logging
from database import Session
from models import Batch
from utils.stability_helpers import (
    retry_on_failure, 
    safe_database_operation,
    CircuitBreaker,
    validate_batch_data,
    log_operation,
    HealthChecker
)

logger = logging.getLogger(__name__)

# Create circuit breakers for external services
rag_api_breaker = CircuitBreaker(failure_threshold=5, recovery_timeout=60)
knowledge_db_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)


class StableBatchService:
    """
    Example of BatchService with stability improvements.
    This shows how to integrate the stability helpers.
    """
    
    def __init__(self):
        self.health_checker = HealthChecker()
        self._register_health_checks()
        
    def _register_health_checks(self):
        """Register health checks for the service."""
        self.health_checker.register_check("knowledgesync_database", self._check_knowledgesync_db)
        self.health_checker.register_check("knowledge_database", self._check_knowledge_db)
        self.health_checker.register_check("rag_api", self._check_rag_api)
        
    @retry_on_failure(max_retries=3, delay=0.5)
    def _check_knowledgesync_db(self) -> bool:
        """Check KnowledgeSync database connectivity (main application database)."""
        try:
            session = Session()
            session.execute("SELECT 1")
            session.close()
            return True
        except Exception:
            return False
            
    @retry_on_failure(max_retries=3, delay=0.5)
    def _check_knowledge_db(self) -> bool:
        """Check KnowledgeDocuments database connectivity."""
        try:
            import psycopg2
            conn = psycopg2.connect(
                host="studio.local",
                database="KnowledgeDocuments",
                user="postgres",
                password="prodogs03",
                port=5432
            )
            cursor = conn.cursor()
            cursor.execute("SELECT 1")
            cursor.close()
            conn.close()
            return True
        except Exception:
            return False
            
    def _check_rag_api(self) -> bool:
        """Check RAG API availability."""
        try:
            import requests
            # Replace with actual RAG API health endpoint
            response = requests.get("http://your-rag-api/health", timeout=5)
            return response.status_code == 200
        except Exception:
            return False
    
    @log_operation("create", "batch", "batch_name")
    @retry_on_failure(max_retries=3, delay=1.0)
    def create_batch_with_stability(self, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a batch with full stability features.
        
        Args:
            batch_data: Dictionary containing batch configuration
            
        Returns:
            Dict with batch creation results
        """
        # Step 1: Validate input
        try:
            validated_data = validate_batch_data(batch_data)
        except ValueError as e:
            logger.error(f"Batch validation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'validation'
            }
        
        # Step 2: Check system health
        if not self.health_checker.is_healthy():
            health_status = self.health_checker.check_all()
            unhealthy = [k for k, v in health_status.items() if not v]
            logger.warning(f"System not fully healthy. Failed checks: {unhealthy}")
            
            # Allow continuation if only RAG API is down
            if 'knowledgesync_database' in unhealthy or 'knowledge_database' in unhealthy:
                return {
                    'success': False,
                    'error': 'Critical services unavailable',
                    'health_status': health_status
                }
        
        # Step 3: Create batch with transaction safety
        session = Session()
        try:
            with safe_database_operation(session, "batch_creation"):
                # Create batch logic here
                batch = Batch(
                    batch_name=validated_data.get('batch_name'),
                    folder_ids=validated_data['folder_ids'],
                    # ... other fields
                )
                session.add(batch)
                session.flush()  # Get batch ID
                
                batch_id = batch.id
                logger.info(f"Created batch {batch_id} successfully")
                
                # Step 4: Stage to KnowledgeDocuments with circuit breaker
                staging_result = self._stage_with_circuit_breaker(batch_id, validated_data)
                
                if not staging_result['success']:
                    # Rollback will happen automatically
                    raise Exception(f"Staging failed: {staging_result['error']}")
                
                return {
                    'success': True,
                    'batch_id': batch_id,
                    'message': 'Batch created and staged successfully',
                    'health_status': self.health_checker.check_all()
                }
                
        except Exception as e:
            logger.error(f"Batch creation failed: {e}")
            return {
                'success': False,
                'error': str(e),
                'error_type': 'processing'
            }
    
    @knowledge_db_breaker
    def _stage_with_circuit_breaker(self, batch_id: int, batch_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Stage batch with circuit breaker protection.
        
        This prevents cascading failures if KnowledgeDocuments DB is down.
        """
        try:
            # Staging logic here
            logger.info(f"Staging batch {batch_id} to KnowledgeDocuments")
            
            # Simulate staging
            # ... actual staging code ...
            
            return {'success': True}
            
        except Exception as e:
            logger.error(f"Staging failed for batch {batch_id}: {e}")
            return {'success': False, 'error': str(e)}
    
    @rag_api_breaker
    @retry_on_failure(max_retries=3, delay=2.0, backoff=2.0)
    def call_rag_api_safely(self, llm_config: Dict[str, Any], prompt: str, content: str) -> Dict[str, Any]:
        """
        Call RAG API with circuit breaker and retry logic.
        
        This prevents the system from repeatedly calling a failing API.
        """
        try:
            import requests
            
            # Use the unified formatter
            from utils.llm_config_formatter import format_llm_config_for_rag_api
            formatted_config = format_llm_config_for_rag_api(llm_config)
            
            # Make API call
            response = requests.post(
                f"{formatted_config['url']}/api/generate",
                json={
                    'prompt': prompt,
                    'content': content,
                    'model': formatted_config['model_name']
                },
                timeout=30
            )
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            logger.error("RAG API call timed out")
            raise
        except requests.exceptions.RequestException as e:
            logger.error(f"RAG API call failed: {e}")
            raise
    
    def get_service_status(self) -> Dict[str, Any]:
        """
        Get comprehensive service status.
        
        Returns:
            Dict containing service health and statistics
        """
        return {
            'health': self.health_checker.check_all(),
            'circuit_breakers': {
                'rag_api': {
                    'state': rag_api_breaker.state,
                    'failure_count': rag_api_breaker.failure_count
                },
                'knowledge_db': {
                    'state': knowledge_db_breaker.state,
                    'failure_count': knowledge_db_breaker.failure_count
                }
            },
            'is_operational': self.health_checker.is_healthy()
        }


# Example usage
if __name__ == "__main__":
    service = StableBatchService()
    
    # Check service status
    status = service.get_service_status()
    print(f"Service status: {status}")
    
    # Create a batch with stability features
    result = service.create_batch_with_stability({
        'folder_ids': [1, 2],
        'connection_ids': [1],
        'prompt_ids': [1, 2, 3],
        'batch_name': 'Test batch with stability'
    })
    
    print(f"Batch creation result: {result}")