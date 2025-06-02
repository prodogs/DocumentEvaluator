"""
Middleware and Error Handling

Provides request/response middleware, error handlers, and monitoring.
"""

import uuid
import time
import logging
from datetime import datetime
from functools import wraps
from typing import Dict, Any, Optional, Tuple

from flask import request, g, jsonify, current_app
from werkzeug.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError

from app.core.logger import get_logger, log_request, log_response

logger = get_logger(__name__)


# Custom Exceptions
class APIError(Exception):
    """Base API exception with structured error response"""
    
    def __init__(self, message: str, status_code: int = 400, 
                 details: Optional[Dict[str, Any]] = None, error_code: Optional[str] = None):
        super().__init__(message)
        self.message = message
        self.status_code = status_code
        self.details = details or {}
        self.error_code = error_code or self.__class__.__name__
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for JSON response"""
        return {
            'error': {
                'message': self.message,
                'code': self.error_code,
                'details': self.details,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            },
            'request_id': getattr(g, 'request_id', None)
        }


class ValidationError(APIError):
    """Validation error for request data"""
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        details = kwargs.get('details', {})
        if field:
            details['field'] = field
        super().__init__(message, status_code=422, details=details, **kwargs)


class NotFoundError(APIError):
    """Resource not found error"""
    def __init__(self, resource: str, identifier: Any = None, **kwargs):
        message = f"{resource} not found"
        if identifier:
            message += f": {identifier}"
        super().__init__(message, status_code=404, **kwargs)


class AuthenticationError(APIError):
    """Authentication required error"""
    def __init__(self, message: str = "Authentication required", **kwargs):
        super().__init__(message, status_code=401, **kwargs)


class AuthorizationError(APIError):
    """Authorization failed error"""
    def __init__(self, message: str = "Access denied", **kwargs):
        super().__init__(message, status_code=403, **kwargs)


class RateLimitError(APIError):
    """Rate limit exceeded error"""
    def __init__(self, message: str = "Rate limit exceeded", retry_after: Optional[int] = None, **kwargs):
        details = kwargs.get('details', {})
        if retry_after:
            details['retry_after'] = retry_after
        super().__init__(message, status_code=429, details=details, **kwargs)


class ServiceUnavailableError(APIError):
    """External service unavailable error"""
    def __init__(self, service: str, message: Optional[str] = None, **kwargs):
        msg = f"{service} service is currently unavailable"
        if message:
            msg += f": {message}"
        super().__init__(msg, status_code=503, **kwargs)


# Middleware Functions
def setup_request_context():
    """Set up request context with tracking information"""
    # Generate or extract request ID
    g.request_id = request.headers.get('X-Request-ID', str(uuid.uuid4()))
    g.request_start_time = time.time()
    g.user_id = None  # Will be set by auth middleware
    
    # Log request
    log_request(request, g.request_id)


def teardown_request_context(response):
    """Clean up request context and log response"""
    # Calculate request duration
    if hasattr(g, 'request_start_time'):
        duration = time.time() - g.request_start_time
        response.headers['X-Request-Duration-ms'] = str(int(duration * 1000))
    
    # Add request ID to response
    if hasattr(g, 'request_id'):
        response.headers['X-Request-ID'] = g.request_id
    
    # Log response
    log_response(response, getattr(g, 'request_id', None))
    
    return response


# Error Handlers
def handle_api_error(error: APIError) -> Tuple[Dict[str, Any], int]:
    """Handle custom API errors"""
    logger.warning(f"API Error: {error.message}", extra={
        'request_id': getattr(g, 'request_id', None),
        'error_code': error.error_code,
        'status_code': error.status_code,
        'details': error.details
    })
    return jsonify(error.to_dict()), error.status_code


def handle_http_error(error: HTTPException) -> Tuple[Dict[str, Any], int]:
    """Handle Werkzeug HTTP exceptions"""
    logger.warning(f"HTTP Error: {error}", extra={
        'request_id': getattr(g, 'request_id', None),
        'status_code': error.code
    })
    return jsonify({
        'error': {
            'message': error.description or str(error),
            'code': error.name,
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        },
        'request_id': getattr(g, 'request_id', None)
    }), error.code or 500


def handle_database_error(error: SQLAlchemyError) -> Tuple[Dict[str, Any], int]:
    """Handle database errors"""
    logger.error(f"Database Error: {error}", exc_info=True, extra={
        'request_id': getattr(g, 'request_id', None)
    })
    
    # Don't expose internal database errors in production
    if current_app.debug:
        message = str(error)
    else:
        message = "A database error occurred"
    
    return jsonify({
        'error': {
            'message': message,
            'code': 'DATABASE_ERROR',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        },
        'request_id': getattr(g, 'request_id', None)
    }), 500


def handle_general_error(error: Exception) -> Tuple[Dict[str, Any], int]:
    """Handle unexpected errors"""
    logger.error(f"Unexpected Error: {error}", exc_info=True, extra={
        'request_id': getattr(g, 'request_id', None)
    })
    
    # Don't expose internal errors in production
    if current_app.debug:
        message = str(error)
    else:
        message = "An unexpected error occurred"
    
    return jsonify({
        'error': {
            'message': message,
            'code': 'INTERNAL_ERROR',
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        },
        'request_id': getattr(g, 'request_id', None)
    }), 500


# Decorators
def monitor_performance(func):
    """Monitor endpoint performance"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        start_time = time.time()
        try:
            result = func(*args, **kwargs)
            execution_time = time.time() - start_time
            
            # Log slow endpoints
            if execution_time > 1.0:
                logger.warning(
                    f"Slow endpoint: {request.endpoint} took {execution_time:.2f}s",
                    extra={
                        'request_id': getattr(g, 'request_id', None),
                        'endpoint': request.endpoint,
                        'method': request.method,
                        'execution_time': execution_time
                    }
                )
            
            return result
        except Exception as e:
            execution_time = time.time() - start_time
            logger.error(
                f"Endpoint error: {request.endpoint} failed after {execution_time:.2f}s",
                exc_info=True,
                extra={
                    'request_id': getattr(g, 'request_id', None),
                    'endpoint': request.endpoint,
                    'method': request.method,
                    'execution_time': execution_time
                }
            )
            raise
    return wrapper


def validate_json(*required_fields):
    """Validate JSON request data"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not request.is_json:
                raise ValidationError("Request must be JSON")
            
            data = request.get_json()
            if not data:
                raise ValidationError("Request body cannot be empty")
            
            # Check required fields
            missing_fields = [field for field in required_fields if field not in data]
            if missing_fields:
                raise ValidationError(
                    f"Missing required fields: {', '.join(missing_fields)}",
                    details={'missing_fields': missing_fields}
                )
            
            return func(*args, **kwargs)
        return wrapper
    return decorator


def require_auth(func):
    """Require authentication for endpoint"""
    @wraps(func)
    def wrapper(*args, **kwargs):
        # TODO: Implement actual authentication check
        # For now, just check for a mock auth header
        auth_header = request.headers.get('Authorization')
        if not auth_header:
            raise AuthenticationError()
        
        # Set user context
        g.user_id = 'mock_user'  # TODO: Extract from token
        
        return func(*args, **kwargs)
    return wrapper


def rate_limit(max_requests: int = 100, window: int = 3600):
    """Rate limit decorator (requires Redis)"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            if not current_app.config.get('RATELIMIT_ENABLED'):
                return func(*args, **kwargs)
            
            # TODO: Implement actual rate limiting with Redis
            # For now, just pass through
            return func(*args, **kwargs)
        return wrapper
    return decorator


# Initialize middleware with Flask app
def init_middleware(app):
    """Initialize all middleware with Flask app"""
    
    # Request lifecycle
    app.before_request(setup_request_context)
    app.after_request(teardown_request_context)
    
    # Error handlers
    app.register_error_handler(APIError, handle_api_error)
    app.register_error_handler(HTTPException, handle_http_error)
    app.register_error_handler(SQLAlchemyError, handle_database_error)
    app.register_error_handler(Exception, handle_general_error)
    
    # Add performance monitoring to all routes
    for rule in app.url_map.iter_rules():
        if rule.endpoint and rule.endpoint != 'static':
            view_func = app.view_functions.get(rule.endpoint)
            if view_func:
                app.view_functions[rule.endpoint] = monitor_performance(view_func)
    
    logger.info("Middleware initialized")


# Health check middleware
def health_check_response():
    """Standard health check response"""
    from app.core.database import db_manager
    
    # Check database
    db_healthy = db_manager.health_check()
    
    # Check Redis if enabled
    redis_healthy = True
    if current_app.config.get('CACHE_TYPE') == 'redis':
        try:
            import redis
            r = redis.from_url(current_app.config.get('REDIS_URL'))
            r.ping()
        except:
            redis_healthy = False
    
    # Overall health
    is_healthy = db_healthy and redis_healthy
    
    health_data = {
        'status': 'healthy' if is_healthy else 'unhealthy',
        'timestamp': datetime.utcnow().isoformat() + 'Z',
        'version': current_app.config.get('VERSION', 'unknown'),
        'checks': {
            'database': 'ok' if db_healthy else 'failed',
            'redis': 'ok' if redis_healthy else 'failed'
        }
    }
    
    return jsonify(health_data), 200 if is_healthy else 503