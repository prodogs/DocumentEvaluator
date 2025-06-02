"""
Structured Logging Module

Provides structured logging with request tracking, performance metrics, and error context.
"""

import logging
import json
import sys
import traceback
from datetime import datetime
from typing import Dict, Any, Optional, Union
from pathlib import Path
from logging.handlers import RotatingFileHandler, TimedRotatingFileHandler

from flask import request, has_request_context, g
from pythonjsonlogger import jsonlogger

from app.core.config import get_config


class RequestContextFilter(logging.Filter):
    """Add request context to log records"""
    
    def filter(self, record):
        """Add request context fields to log record"""
        if has_request_context():
            record.request_id = getattr(g, 'request_id', None)
            record.user_id = getattr(g, 'user_id', None)
            record.endpoint = request.endpoint
            record.method = request.method
            record.path = request.path
            record.ip = request.remote_addr
        else:
            record.request_id = None
            record.user_id = None
            record.endpoint = None
            record.method = None
            record.path = None
            record.ip = None
        
        return True


class StructuredFormatter(jsonlogger.JsonFormatter):
    """Custom JSON formatter with additional fields"""
    
    def add_fields(self, log_record, record, message_dict):
        """Add custom fields to log record"""
        super().add_fields(log_record, record, message_dict)
        
        # Add timestamp
        log_record['timestamp'] = datetime.utcnow().isoformat() + 'Z'
        
        # Add level name
        log_record['level'] = record.levelname
        
        # Add logger name
        log_record['logger'] = record.name
        
        # Add source location
        log_record['source'] = {
            'file': record.pathname,
            'line': record.lineno,
            'function': record.funcName
        }
        
        # Add exception info if present
        if record.exc_info:
            log_record['exception'] = {
                'type': record.exc_info[0].__name__,
                'message': str(record.exc_info[1]),
                'traceback': traceback.format_exception(*record.exc_info)
            }
        
        # Add request context if available
        if hasattr(record, 'request_id') and record.request_id:
            log_record['request'] = {
                'id': record.request_id,
                'user_id': record.user_id,
                'endpoint': record.endpoint,
                'method': record.method,
                'path': record.path,
                'ip': record.ip
            }


class PerformanceLogger:
    """Logger for performance metrics"""
    
    def __init__(self, logger):
        self.logger = logger
    
    def log_operation(self, operation: str, duration: float, 
                     success: bool = True, metadata: Optional[Dict[str, Any]] = None):
        """Log operation performance"""
        data = {
            'operation': operation,
            'duration_ms': round(duration * 1000, 2),
            'success': success
        }
        
        if metadata:
            data['metadata'] = metadata
        
        level = logging.INFO if success else logging.WARNING
        self.logger.log(level, f"Operation: {operation}", extra={'performance': data})
    
    def log_database_query(self, query: str, duration: float, 
                          row_count: Optional[int] = None):
        """Log database query performance"""
        data = {
            'query': query[:200] + '...' if len(query) > 200 else query,
            'duration_ms': round(duration * 1000, 2)
        }
        
        if row_count is not None:
            data['row_count'] = row_count
        
        level = logging.WARNING if duration > 1.0 else logging.DEBUG
        self.logger.log(level, "Database query", extra={'database': data})
    
    def log_api_call(self, service: str, endpoint: str, method: str,
                    duration: float, status_code: int, 
                    metadata: Optional[Dict[str, Any]] = None):
        """Log external API call performance"""
        data = {
            'service': service,
            'endpoint': endpoint,
            'method': method,
            'duration_ms': round(duration * 1000, 2),
            'status_code': status_code,
            'success': 200 <= status_code < 300
        }
        
        if metadata:
            data['metadata'] = metadata
        
        level = logging.WARNING if status_code >= 500 or duration > 5.0 else logging.INFO
        self.logger.log(level, f"API call to {service}", extra={'api_call': data})


def setup_logging(app=None):
    """Set up structured logging"""
    config = get_config()
    
    # Create logs directory
    log_dir = Path('logs')
    log_dir.mkdir(exist_ok=True)
    
    # Set up root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, config.LOG_LEVEL))
    
    # Remove default handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatters
    json_formatter = StructuredFormatter()
    console_formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Console handler (human-readable in development, JSON in production)
    console_handler = logging.StreamHandler(sys.stdout)
    if config.DEBUG:
        console_handler.setFormatter(console_formatter)
    else:
        console_handler.setFormatter(json_formatter)
    console_handler.addFilter(RequestContextFilter())
    root_logger.addHandler(console_handler)
    
    # File handler (always JSON)
    file_handler = RotatingFileHandler(
        log_dir / config.LOG_FILE,
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    file_handler.setFormatter(json_formatter)
    file_handler.addFilter(RequestContextFilter())
    root_logger.addHandler(file_handler)
    
    # Error file handler
    error_handler = RotatingFileHandler(
        log_dir / 'errors.log',
        maxBytes=10 * 1024 * 1024,  # 10MB
        backupCount=10
    )
    error_handler.setLevel(logging.ERROR)
    error_handler.setFormatter(json_formatter)
    error_handler.addFilter(RequestContextFilter())
    root_logger.addHandler(error_handler)
    
    # Performance log handler
    perf_handler = TimedRotatingFileHandler(
        log_dir / 'performance.log',
        when='midnight',
        interval=1,
        backupCount=30
    )
    perf_handler.setFormatter(json_formatter)
    perf_logger = logging.getLogger('performance')
    perf_logger.addHandler(perf_handler)
    perf_logger.setLevel(logging.INFO)
    
    # Set log levels for noisy libraries
    logging.getLogger('werkzeug').setLevel(logging.WARNING)
    logging.getLogger('urllib3').setLevel(logging.WARNING)
    logging.getLogger('sqlalchemy.engine').setLevel(
        logging.INFO if config.DEBUG else logging.WARNING
    )
    
    return root_logger


def get_logger(name: str) -> logging.Logger:
    """Get a logger instance with the given name"""
    return logging.getLogger(name)


def get_performance_logger(name: str) -> PerformanceLogger:
    """Get a performance logger instance"""
    logger = logging.getLogger(f'performance.{name}')
    return PerformanceLogger(logger)


# Utility logging functions
def log_request(req: request, request_id: str):
    """Log incoming request"""
    logger = get_logger('access')
    
    # Get request body for POST/PUT/PATCH
    body = None
    if req.method in ['POST', 'PUT', 'PATCH'] and req.is_json:
        try:
            body = req.get_json()
            # Mask sensitive fields
            if body and isinstance(body, dict):
                body = mask_sensitive_data(body.copy())
        except:
            body = '[Invalid JSON]'
    
    logger.info(
        f"{req.method} {req.path}",
        extra={
            'http_request': {
                'method': req.method,
                'path': req.path,
                'query': dict(req.args),
                'headers': dict(req.headers),
                'body': body,
                'remote_addr': req.remote_addr,
                'user_agent': req.user_agent.string
            }
        }
    )


def log_response(response, request_id: str):
    """Log outgoing response"""
    logger = get_logger('access')
    
    # Log response
    logger.info(
        f"Response {response.status_code}",
        extra={
            'http_response': {
                'status_code': response.status_code,
                'headers': dict(response.headers),
                'size': response.content_length
            }
        }
    )


def log_error(error: Exception, context: Optional[Dict[str, Any]] = None):
    """Log error with context"""
    logger = get_logger('error')
    
    error_data = {
        'error_type': type(error).__name__,
        'error_message': str(error),
        'traceback': traceback.format_exc()
    }
    
    if context:
        error_data['context'] = context
    
    logger.error(
        f"{type(error).__name__}: {str(error)}",
        extra={'error_details': error_data},
        exc_info=True
    )


def log_security_event(event_type: str, details: Dict[str, Any], 
                      severity: str = 'warning'):
    """Log security-related events"""
    logger = get_logger('security')
    
    level = getattr(logging, severity.upper(), logging.WARNING)
    logger.log(
        level,
        f"Security event: {event_type}",
        extra={
            'security_event': {
                'type': event_type,
                'details': details,
                'timestamp': datetime.utcnow().isoformat() + 'Z'
            }
        }
    )


def mask_sensitive_data(data: Union[Dict, list, str]) -> Union[Dict, list, str]:
    """Mask sensitive data in logs"""
    sensitive_fields = {
        'password', 'api_key', 'secret', 'token', 'authorization',
        'credit_card', 'ssn', 'email', 'phone'
    }
    
    if isinstance(data, dict):
        masked = {}
        for key, value in data.items():
            if any(field in key.lower() for field in sensitive_fields):
                masked[key] = '[REDACTED]'
            else:
                masked[key] = mask_sensitive_data(value)
        return masked
    elif isinstance(data, list):
        return [mask_sensitive_data(item) for item in data]
    else:
        return data


# Audit logging
class AuditLogger:
    """Logger for audit events"""
    
    def __init__(self):
        self.logger = logging.getLogger('audit')
        
        # Set up audit log handler
        handler = TimedRotatingFileHandler(
            'logs/audit.log',
            when='midnight',
            interval=1,
            backupCount=90  # Keep 90 days of audit logs
        )
        handler.setFormatter(StructuredFormatter())
        self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
    
    def log_event(self, event_type: str, entity_type: str, entity_id: Any,
                 action: str, user_id: Optional[str] = None,
                 details: Optional[Dict[str, Any]] = None):
        """Log an audit event"""
        audit_data = {
            'event_type': event_type,
            'entity_type': entity_type,
            'entity_id': entity_id,
            'action': action,
            'user_id': user_id or getattr(g, 'user_id', None),
            'timestamp': datetime.utcnow().isoformat() + 'Z'
        }
        
        if details:
            audit_data['details'] = details
        
        if has_request_context():
            audit_data['request'] = {
                'ip': request.remote_addr,
                'user_agent': request.user_agent.string,
                'endpoint': request.endpoint
            }
        
        self.logger.info(
            f"Audit: {event_type} - {action} on {entity_type}:{entity_id}",
            extra={'audit': audit_data}
        )


# Global audit logger instance
audit_logger = AuditLogger()