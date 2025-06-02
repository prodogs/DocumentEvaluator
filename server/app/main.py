"""
Main Application Module

Creates and configures the Flask application using the new modular structure.
"""

import os
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from flask import Flask
from flask_cors import CORS

from app.core.config import get_config, validate_config
from app.core.database import init_db, close_db
from app.core.middleware import init_middleware, health_check_response
from app.core.logger import setup_logging, get_logger
from app.core.cache import init_cache
from app.utils.async_utils import async_runner


def create_app(config_name=None):
    """Application factory pattern"""
    
    # Get configuration
    config = get_config(config_name)
    
    # Create Flask app
    app = Flask(__name__)
    app.config.from_object(config)
    
    # Initialize configuration
    config.init_app(app)
    
    # Set up logging first
    setup_logging(app)
    logger = get_logger(__name__)
    logger.info(f"Creating application with config: {config.__class__.__name__}")
    
    # Validate configuration
    try:
        validate_config()
    except ValueError as e:
        logger.error(f"Configuration validation failed: {e}")
        if not app.debug:
            sys.exit(1)
    
    # Initialize extensions
    init_extensions(app)
    
    # Register blueprints
    register_blueprints(app)
    
    # Initialize middleware
    init_middleware(app)
    
    # Register teardown handlers
    app.teardown_appcontext(close_db)
    
    # Add health check endpoint
    @app.route('/health')
    def health():
        return health_check_response()
    
    # Log startup info
    logger.info(f"Application initialized successfully")
    logger.info(f"Debug mode: {app.debug}")
    logger.info(f"Environment: {app.config.get('ENV', 'default')}")
    
    return app


def init_extensions(app):
    """Initialize Flask extensions"""
    logger = get_logger(__name__)
    
    # Initialize database
    try:
        init_db(app)
        logger.info("Database initialized")
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        raise
    
    # Initialize cache
    try:
        init_cache(app)
        logger.info("Cache initialized")
    except Exception as e:
        logger.warning(f"Failed to initialize cache: {e}")
    
    # Initialize CORS
    CORS(app, 
         origins=app.config.get('CORS_ORIGINS', ['http://localhost:5173']),
         supports_credentials=True)
    logger.info("CORS initialized")
    
    # Start async runner if enabled
    if app.config.get('ENABLE_ASYNC', True):
        async_runner.start()
        logger.info("Async runner started")
        
        # Register cleanup
        import atexit
        atexit.register(async_runner.stop)


def register_blueprints(app):
    """Register application blueprints"""
    logger = get_logger(__name__)
    
    # Import and register API blueprints
    try:
        # Import existing route modules
        from api.batch_routes import register_batch_routes
        from api.folder_routes import register_folder_routes
        from api.document_routes import register_document_routes
        from api.model_routes import register_model_routes
        from api.connection_routes import register_connection_routes
        from api.llm_provider_routes import register_llm_provider_routes
        from api.service_routes import register_service_routes
        from api.maintenance_routes import register_maintenance_routes
        
        # Register routes
        register_batch_routes(app)
        register_folder_routes(app)
        register_document_routes(app)
        register_model_routes(app)
        register_connection_routes(app)
        register_llm_provider_routes(app)
        register_service_routes(app)
        register_maintenance_routes(app)
        
        logger.info("All routes registered successfully")
        
    except ImportError as e:
        logger.error(f"Failed to import routes: {e}")
        raise


def register_cli_commands(app):
    """Register CLI commands"""
    
    @app.cli.command()
    def init_db_command():
        """Initialize the database."""
        from app.core.database import db_manager
        from models import Base
        
        Base.metadata.create_all(bind=db_manager.engine)
        print("Database initialized.")
    
    @app.cli.command()
    def clear_cache():
        """Clear all cache entries."""
        from app.core.cache import cache
        
        if cache:
            count = cache.clear()
            print(f"Cleared {count} cache entries.")
        else:
            print("Cache not initialized.")
    
    @app.cli.command()
    def check_config():
        """Validate configuration."""
        try:
            validate_config()
            print("Configuration is valid.")
        except ValueError as e:
            print(f"Configuration error: {e}")
            sys.exit(1)


# Import and register additional utilities
def register_admin_routes(app):
    """Register admin/debug routes (development only)"""
    if not app.debug:
        return
    
    @app.route('/api/admin/cache/stats')
    def cache_stats():
        from app.core.cache import get_cache_stats
        return get_cache_stats()
    
    @app.route('/api/admin/db/pool')
    def db_pool_status():
        from app.core.database import get_pool_status
        return get_pool_status()
    
    @app.route('/api/admin/config')
    def show_config():
        # Show non-sensitive config values
        safe_keys = ['APP_NAME', 'VERSION', 'DEBUG', 'LOG_LEVEL', 'CORS_ORIGINS']
        return {k: app.config.get(k) for k in safe_keys}


# Create application instance for development
if __name__ == '__main__':
    # Create app
    app = create_app('development')
    
    # Register CLI commands
    register_cli_commands(app)
    
    # Register admin routes
    register_admin_routes(app)
    
    # Get configuration
    config = get_config('development')
    
    # Run application
    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        use_reloader=True
    )