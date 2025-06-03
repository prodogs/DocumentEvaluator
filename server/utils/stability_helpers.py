"""
Stability Helpers - Quick wins for immediate stability improvements
"""

import time
import logging
import functools
from typing import Callable, Any, Optional, Dict
from contextlib import contextmanager
import psycopg2
from sqlalchemy.exc import OperationalError, IntegrityError

logger = logging.getLogger(__name__)


def retry_on_failure(max_retries: int = 3, delay: float = 1.0, backoff: float = 2.0):
    """
    Decorator to retry function calls on failure with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        delay: Initial delay between retries in seconds
        backoff: Multiplier for delay after each retry
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            current_delay = delay
            
            for attempt in range(max_retries + 1):
                try:
                    if attempt > 0:
                        logger.info(f"Retrying {func.__name__} (attempt {attempt + 1}/{max_retries + 1})")
                    return func(*args, **kwargs)
                    
                except (OperationalError, psycopg2.OperationalError) as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Database connection error in {func.__name__}: {e}. Retrying in {current_delay}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"Failed after {max_retries + 1} attempts: {e}")
                        
                except IntegrityError as e:
                    # Don't retry integrity errors
                    logger.error(f"Integrity error in {func.__name__}: {e}")
                    raise
                    
                except Exception as e:
                    last_exception = e
                    if attempt < max_retries:
                        logger.warning(f"Error in {func.__name__}: {e}. Retrying in {current_delay}s...")
                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(f"Failed after {max_retries + 1} attempts: {e}")
            
            raise last_exception
        
        return wrapper
    return decorator


@contextmanager
def safe_database_operation(session, operation_name: str = "database operation"):
    """
    Context manager for safe database operations with automatic rollback.
    
    Args:
        session: SQLAlchemy session
        operation_name: Name of the operation for logging
    """
    try:
        yield session
        session.commit()
        logger.debug(f"Successfully committed {operation_name}")
    except IntegrityError as e:
        session.rollback()
        logger.error(f"Integrity error in {operation_name}: {e}")
        raise
    except Exception as e:
        session.rollback()
        logger.error(f"Error in {operation_name}: {e}")
        raise
    finally:
        session.close()


class CircuitBreaker:
    """
    Circuit breaker pattern implementation to prevent cascading failures.
    """
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time: Optional[float] = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def __call__(self, func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            if self.state == "OPEN":
                if self._should_attempt_reset():
                    self.state = "HALF_OPEN"
                    logger.info(f"Circuit breaker for {func.__name__} is HALF_OPEN, attempting reset")
                else:
                    time_remaining = self.recovery_timeout - (time.time() - self.last_failure_time)
                    raise Exception(f"Circuit breaker is OPEN. Service will retry in {time_remaining:.0f} seconds")
            
            try:
                result = func(*args, **kwargs)
                self._on_success(func.__name__)
                return result
            except Exception as e:
                self._on_failure(func.__name__)
                raise
                
        return wrapper
    
    def _should_attempt_reset(self) -> bool:
        return (
            self.last_failure_time and 
            time.time() - self.last_failure_time >= self.recovery_timeout
        )
    
    def _on_success(self, func_name: str):
        if self.state == "HALF_OPEN":
            logger.info(f"Circuit breaker for {func_name} is now CLOSED")
        self.failure_count = 0
        self.state = "CLOSED"
    
    def _on_failure(self, func_name: str):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.error(f"Circuit breaker for {func_name} is now OPEN after {self.failure_count} failures")


def validate_batch_data(batch_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate batch data before processing.
    
    Args:
        batch_data: Dictionary containing batch configuration
        
    Returns:
        Validated batch data
        
    Raises:
        ValueError: If validation fails
    """
    errors = []
    
    # Check required fields
    required_fields = ['folder_ids', 'connection_ids', 'prompt_ids']
    for field in required_fields:
        if field not in batch_data:
            errors.append(f"Missing required field: {field}")
        elif not batch_data[field]:
            errors.append(f"Empty {field} list")
        elif not isinstance(batch_data[field], list):
            errors.append(f"{field} must be a list")
        elif not all(isinstance(x, int) for x in batch_data[field]):
            errors.append(f"{field} must contain only integers")
    
    # Validate batch name if provided
    if 'batch_name' in batch_data:
        if not isinstance(batch_data['batch_name'], str):
            errors.append("batch_name must be a string")
        elif len(batch_data['batch_name']) > 255:
            errors.append("batch_name too long (max 255 characters)")
    
    if errors:
        raise ValueError(f"Batch validation failed: {'; '.join(errors)}")
    
    return batch_data


def log_operation(operation_type: str, entity_type: str, entity_id: Any):
    """
    Decorator to log operations for audit trail.
    
    Args:
        operation_type: Type of operation (create, update, delete)
        entity_type: Type of entity (batch, document, etc.)
        entity_id: ID of the entity
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            start_time = time.time()
            
            # Extract entity_id if it's a parameter name
            actual_id = entity_id
            if isinstance(entity_id, str) and entity_id in kwargs:
                actual_id = kwargs[entity_id]
            elif isinstance(entity_id, int) and entity_id < len(args):
                actual_id = args[entity_id]
            
            logger.info(f"Starting {operation_type} on {entity_type} {actual_id}")
            
            try:
                result = func(*args, **kwargs)
                duration = time.time() - start_time
                logger.info(f"Completed {operation_type} on {entity_type} {actual_id} in {duration:.2f}s")
                return result
            except Exception as e:
                duration = time.time() - start_time
                logger.error(f"Failed {operation_type} on {entity_type} {actual_id} after {duration:.2f}s: {e}")
                raise
                
        return wrapper
    return decorator


class HealthChecker:
    """
    Simple health checker for critical services.
    """
    def __init__(self):
        self.checks = {}
        
    def register_check(self, name: str, check_func: Callable[[], bool]):
        """Register a health check function."""
        self.checks[name] = check_func
        
    def check_all(self) -> Dict[str, bool]:
        """Run all health checks and return results."""
        results = {}
        for name, check_func in self.checks.items():
            try:
                results[name] = check_func()
            except Exception as e:
                logger.error(f"Health check '{name}' failed: {e}")
                results[name] = False
        return results
    
    def is_healthy(self) -> bool:
        """Return True if all checks pass."""
        results = self.check_all()
        return all(results.values())


# Example usage:
if __name__ == "__main__":
    # Example of retry decorator
    @retry_on_failure(max_retries=3, delay=1.0)
    def unstable_database_operation():
        # Simulated database operation
        pass
    
    # Example of circuit breaker
    rag_api_breaker = CircuitBreaker(failure_threshold=3, recovery_timeout=30)
    
    @rag_api_breaker
    def call_rag_api(data):
        # API call implementation
        pass
    
    # Example of health checker
    health_checker = HealthChecker()
    health_checker.register_check("database", lambda: True)  # Replace with actual check
    health_checker.register_check("rag_api", lambda: True)   # Replace with actual check
    
    print(f"System health: {health_checker.check_all()}")