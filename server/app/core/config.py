"""
Configuration Management Module

Provides environment-based configuration with validation and defaults.
"""

import os
from typing import Optional
from pathlib import Path


class Config:
    """Base configuration class"""
    
    # Application settings
    APP_NAME = "DocumentEvaluator"
    VERSION = "1.0.0"
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Server settings
    HOST = os.environ.get('HOST', '0.0.0.0')
    PORT = int(os.environ.get('PORT', 5001))
    DEBUG = False
    TESTING = False
    
    # Database settings
    SQLALCHEMY_DATABASE_URI = os.environ.get(
        'DATABASE_URL',
        'postgresql://postgres:prodogs03@studio.local:5432/doc_eval'
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': int(os.environ.get('DB_POOL_SIZE', 10)),
        'pool_recycle': int(os.environ.get('DB_POOL_RECYCLE', 3600)),
        'pool_pre_ping': True,
        'max_overflow': int(os.environ.get('DB_MAX_OVERFLOW', 20))
    }
    
    # Redis settings (for caching and async tasks)
    REDIS_URL = os.environ.get('REDIS_URL', 'redis://localhost:6379/0')
    CACHE_TYPE = 'redis'
    CACHE_REDIS_URL = REDIS_URL
    CACHE_DEFAULT_TIMEOUT = int(os.environ.get('CACHE_TIMEOUT', 300))
    
    # CORS settings
    CORS_ORIGINS = os.environ.get('CORS_ORIGINS', 'http://localhost:5173').split(',')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.environ.get('LOG_FILE', 'app.log')
    
    # File upload settings
    MAX_CONTENT_LENGTH = int(os.environ.get('MAX_UPLOAD_SIZE', 16 * 1024 * 1024))  # 16MB
    UPLOAD_FOLDER = Path(os.environ.get('UPLOAD_FOLDER', 'temp_uploads'))
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'doc', 'docx', 'rtf', 'odt', 'md'}
    
    # Background task settings
    TASK_TIMEOUT = int(os.environ.get('TASK_TIMEOUT', 3600))  # 1 hour
    MAX_CONCURRENT_TASKS = int(os.environ.get('MAX_CONCURRENT_TASKS', 30))
    
    # API Rate limiting
    RATELIMIT_ENABLED = os.environ.get('RATELIMIT_ENABLED', 'false').lower() == 'true'
    RATELIMIT_DEFAULT = os.environ.get('RATELIMIT_DEFAULT', '100/hour')
    
    # Request tracking
    REQUEST_ID_HEADER = 'X-Request-ID'
    ENABLE_REQUEST_LOGGING = True
    
    # Performance settings
    ENABLE_ASYNC = os.environ.get('ENABLE_ASYNC', 'true').lower() == 'true'
    CONNECTION_POOL_SIZE = int(os.environ.get('CONNECTION_POOL_SIZE', 100))
    REQUEST_TIMEOUT = int(os.environ.get('REQUEST_TIMEOUT', 30))
    
    @classmethod
    def init_app(cls, app):
        """Initialize application with configuration"""
        # Create upload directory if it doesn't exist
        cls.UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)
        
        # Set up logging directory
        log_dir = Path('logs')
        log_dir.mkdir(exist_ok=True)


class DevelopmentConfig(Config):
    """Development configuration"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'
    
    # Development-specific settings
    SQLALCHEMY_ECHO = os.environ.get('SQL_ECHO', 'false').lower() == 'true'
    EXPLAIN_TEMPLATE_LOADING = True
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        print(f"Running in DEVELOPMENT mode on {cls.HOST}:{cls.PORT}")


class ProductionConfig(Config):
    """Production configuration"""
    DEBUG = False
    TESTING = False
    
    # Production security settings
    SESSION_COOKIE_SECURE = True
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    PERMANENT_SESSION_LIFETIME = 3600  # 1 hour
    
    # Stricter settings for production
    RATELIMIT_ENABLED = True
    SSL_REDIRECT = os.environ.get('SSL_REDIRECT', 'true').lower() == 'true'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)
        
        # Log to syslog in production
        import logging
        from logging.handlers import SysLogHandler
        
        if not app.debug:
            syslog_handler = SysLogHandler()
            syslog_handler.setLevel(logging.WARNING)
            app.logger.addHandler(syslog_handler)


class TestingConfig(Config):
    """Testing configuration"""
    TESTING = True
    DEBUG = True
    
    # Use in-memory SQLite for tests
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
    # Disable CSRF for testing
    WTF_CSRF_ENABLED = False
    
    # Use simple cache for testing
    CACHE_TYPE = 'simple'
    
    @classmethod
    def init_app(cls, app):
        Config.init_app(app)


# Configuration dictionary
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'testing': TestingConfig,
    'default': DevelopmentConfig
}


def get_config(config_name: Optional[str] = None) -> Config:
    """Get configuration object based on environment"""
    if config_name is None:
        config_name = os.environ.get('FLASK_ENV', 'development')
    
    return config.get(config_name, config['default'])


# Validation functions
def validate_config():
    """Validate critical configuration settings"""
    config_obj = get_config()
    
    errors = []
    
    # Check database URL
    if not config_obj.SQLALCHEMY_DATABASE_URI:
        errors.append("DATABASE_URL environment variable is not set")
    
    # Check secret key in production
    if config_obj.__class__.__name__ == 'ProductionConfig':
        if config_obj.SECRET_KEY == 'dev-secret-key-change-in-production':
            errors.append("SECRET_KEY must be changed for production")
    
    # Check Redis availability if caching is enabled
    if config_obj.CACHE_TYPE == 'redis':
        try:
            import redis
            r = redis.from_url(config_obj.REDIS_URL)
            r.ping()
        except Exception as e:
            errors.append(f"Redis connection failed: {e}")
    
    if errors:
        raise ValueError(f"Configuration errors: {'; '.join(errors)}")
    
    return True