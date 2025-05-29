#!/usr/bin/env python

'''
Application launcher for the Document Processor API
'''

import os
import sys
import logging
import json
from flask import Flask, request, jsonify, send_from_directory
from concurrent.futures import ThreadPoolExecutor

# Add the parent directory to the Python path to allow package imports
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from server.app import app
from server.routes import register_routes
from server.api.document_routes import background_tasks
from server.api.process_folder import process_folder

# Create a ThreadPoolExecutor
executor = ThreadPoolExecutor(max_workers=10)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('app.log')
    ]
)

logger = logging.getLogger(__name__)

# Set up Swagger UI
def configure_swagger():
    # Get OpenAPI spec path from environment variable or use default
    OPENAPI_SPEC_PATH = os.getenv('OPENAPI_SPEC_PATH', './openapi.json')
    SWAGGER_URL = '/api/docs'
    API_URL = '/static/swagger.json'

    # Create static directory if it doesn't exist
    if not os.path.exists('static'):
        os.makedirs('static')

    # Determine the source of the OpenAPI spec
    source_file = None
    if os.path.exists(OPENAPI_SPEC_PATH):
        source_file = OPENAPI_SPEC_PATH
        logger.info(f"Using OpenAPI spec from {OPENAPI_SPEC_PATH}")
    elif os.path.exists('openapi.json'):
        source_file = 'openapi.json'
        logger.info("Using OpenAPI spec from openapi.json in current directory")

    # If we found a source file, copy it to static/swagger.json
    if source_file:
        import shutil
        logger.info(f"Copying {source_file} to static/swagger.json")
        shutil.copy(source_file, 'static/swagger.json')
    else:
        # If no source file exists, check if static/swagger.json already exists
        if not os.path.exists('static/swagger.json'):
            logger.warning("No OpenAPI spec found, Swagger UI may not work correctly")

    # Verify the file exists and has content
    if os.path.exists('static/swagger.json'):
        size = os.path.getsize('static/swagger.json')
        logger.info(f"static/swagger.json exists with size {size} bytes")

        # If the file is empty or too small, it's probably invalid
        if size < 100:
            logger.warning("swagger.json appears to be empty or too small")

    # Import here to avoid circular imports
    from flask_swagger_ui import get_swaggerui_blueprint

    # Create Swagger UI blueprint
    swagger_ui_blueprint = get_swaggerui_blueprint(
        SWAGGER_URL,
        API_URL,
        config={
            'app_name': "Document Processor API"
        }
    )

    # Register blueprint with Flask app
    app.register_blueprint(swagger_ui_blueprint, url_prefix=SWAGGER_URL)

# Serve the OpenAPI spec
@app.route('/static/swagger.json')
def serve_swagger_spec():
    return send_from_directory('static', 'swagger.json')

# Add a simple health check endpoint
@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'ok',
        'version': '1.0.0'
    })

def main():
    """Main function to launch the Flask application with Swagger UI"""
    try:
        # Configure Swagger UI
        configure_swagger()

        # Register routes
        register_routes(app, background_tasks, process_folder)
        # Note: document_routes are already registered in server/app.py

        # Register service management routes
        from server.api.service_routes import register_service_routes
        register_service_routes(app)

        # Register batch management routes
        from server.api.batch_routes import register_batch_routes
        register_batch_routes(app)

        # Register folder management routes
        from server.api.folder_routes import folder_routes
        app.register_blueprint(folder_routes)

        # Register folder preprocessing routes
        from server.api.folder_preprocessing_routes import folder_preprocessing_bp
        app.register_blueprint(folder_preprocessing_bp)

        # Initialize service integration components
        from server.services.health_monitor import health_monitor
        from server.api.status_polling import polling_service
        from server.services.startup_recovery import startup_recovery_service

        # Start health monitoring
        health_monitor.start_monitoring()
        logger.info("Service health monitoring started")

        # Start status polling service
        polling_service.start_polling()
        logger.info("Status polling service initialized and started")

        # Run startup recovery to check for outstanding tasks
        logger.info("Running startup recovery to check for outstanding tasks...")
        recovery_results = startup_recovery_service.run_startup_recovery()
        logger.info(f"Startup recovery completed: {recovery_results}")

        # Start the dynamic processing queue
        logger.info("Starting dynamic processing queue...")
        from server.services.dynamic_processing_queue import dynamic_queue
        dynamic_queue.start_queue_processing()
        logger.info("Dynamic processing queue started")

        # Start batch cleanup service
        logger.info("Starting batch cleanup service...")
        from server.services.batch_cleanup_service import batch_cleanup_service
        batch_cleanup_service.start_cleanup_service()
        logger.info("Batch cleanup service started")

        # Get port from environment or use default
        port = int(os.getenv('PORT', 5001))

        # Debug: Print all registered routes
        print("\nRegistered Routes:")
        for rule in app.url_map.iter_rules():
            methods = ', '.join(sorted(rule.methods))
            print(f"  {methods:20s} {rule.rule:40s} -> {rule.endpoint}")

        logger.info(f"Starting Document Processor API on port {port}")
        logger.info(f"Swagger UI available at http://localhost:{port}/api/docs")

        # Run Flask app with debug mode enabled for troubleshooting
        print("\nAvailable routes for HTTP requests:")
        for rule in app.url_map.iter_rules():
            methods = ', '.join(sorted(rule.methods - {'HEAD', 'OPTIONS'}))
            print(f"  {methods:20s} {rule.rule}")

        # Check if process-db-folders route is registered
        process_db_folders_route = [rule for rule in app.url_map.iter_rules() if rule.rule == '/process-db-folders']
        if process_db_folders_route:
            print("\n✅ /process-db-folders endpoint is correctly registered")
        else:
            print("\n❌ Warning: /process-db-folders endpoint is NOT registered properly!")
        app.run(host='0.0.0.0', port=port, debug=True)

    except Exception as e:
        logger.error(f"Error starting application: {e}")
        return 1
    finally:
        # Clean up thread resources
        if executor:
            logger.info("Shutting down ThreadPoolExecutor...")
            executor.shutdown(wait=True)

        # Stop service integration components
        try:
            from server.services.health_monitor import health_monitor
            from server.api.status_polling import polling_service
            from server.services.dynamic_processing_queue import dynamic_queue
            from server.services.batch_cleanup_service import batch_cleanup_service

            health_monitor.stop_monitoring_service()
            logger.info("Service health monitoring stopped")

            polling_service.stop_polling_service()
            logger.info("Status polling service stopped")

            dynamic_queue.stop_queue_processing()
            logger.info("Dynamic processing queue stopped")

            batch_cleanup_service.stop_cleanup_service()
            logger.info("Batch cleanup service stopped")
        except Exception as e:
            logger.error(f"Error stopping service integration components: {e}")

        logger.info("Thread resources cleaned up.")

    return 0

if __name__ == '__main__':
    sys.exit(main())
