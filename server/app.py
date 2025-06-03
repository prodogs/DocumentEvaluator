import os
import sys
import time
import threading
import logging
import json
import shutil
from flask import Flask, request, jsonify, send_from_directory
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
from dotenv import load_dotenv

from database import Session
from models import Prompt, Document
from api.document_routes import register_document_routes, background_tasks
from api.process_folder import process_folder
from api.run_batch import run_batch_bp

load_dotenv()  # Load environment variables from .env file

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

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all origins

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

# Configure Swagger UI
configure_swagger()

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

# Register document routes
register_document_routes(app)

# Register batch execution routes
app.register_blueprint(run_batch_bp)

# Register all routes and services
from api.service_routes import register_service_routes
register_service_routes(app)

from api.folder_routes import folder_routes
app.register_blueprint(folder_routes)

from api.folder_preprocessing_routes import folder_preprocessing_bp
app.register_blueprint(folder_preprocessing_bp)

from api.batch_routes import register_batch_routes
register_batch_routes(app)

from api.llm_provider_routes import llm_provider_bp
app.register_blueprint(llm_provider_bp)

from api.model_routes import model_bp
app.register_blueprint(model_bp)

from api.connection_routes import connection_bp
app.register_blueprint(connection_bp)

from api.document_type_routes import document_type_bp
app.register_blueprint(document_type_bp)

from api.maintenance_routes import maintenance_bp
app.register_blueprint(maintenance_bp)

from api.monitoring_routes import register_monitoring_routes
register_monitoring_routes(app)

from api.queue_routes import register_queue_routes
register_queue_routes(app)

from api.llm_responses_routes import llm_responses_bp
app.register_blueprint(llm_responses_bp)

from routes import register_routes
register_routes(app, background_tasks)

# Add route to serve the landing page
@app.route('/')
def index():
    return app.send_static_file('index.html')

# Task cleanup settings
TASK_RETENTION_TIME = 24 * 60 * 60  # 24 hours in seconds

def cleanup_old_tasks():
    """Remove completed tasks older than TASK_RETENTION_TIME from background_tasks dictionary"""
    current_time = time.time()
    tasks_to_remove = []

    for task_id, task_info in background_tasks.items():
        # Skip tasks that are still running
        if task_info['status'] not in ['COMPLETED', 'FAILED']:
            continue

        # Check if task has completion_time; if not, add it now
        if 'completion_time' not in task_info:
            task_info['completion_time'] = current_time
            continue

        # Remove tasks older than retention time
        if current_time - task_info['completion_time'] > TASK_RETENTION_TIME:
            tasks_to_remove.append(task_id)

    # Remove identified tasks
    for task_id in tasks_to_remove:
        del background_tasks[task_id]

    if tasks_to_remove:
        print(f"Cleaned up {len(tasks_to_remove)} old tasks from memory")

# Schedule cleanup_old_tasks to run periodically
def schedule_cleanup():
    """Schedule the cleanup_old_tasks function to run periodically"""
    while True:
        time.sleep(3600)  # Run every hour
        cleanup_old_tasks()

# Start the cleanup thread
cleanup_thread = threading.Thread(target=schedule_cleanup)
cleanup_thread.daemon = True
cleanup_thread.start()

@app.route('/llm-configs', methods=['GET'])
def get_llm_configs():
    """Get all connections (replaces deprecated LLM configurations)"""
    try:
        session = Session()
        from sqlalchemy import text
        # Use raw SQL to get connections with provider information
        configs_result = session.execute(text("""
            SELECT c.id, c.name, c.base_url, m.common_name as model_name,
                   p.provider_type, c.port_no, c.api_key
            FROM connections c
            LEFT JOIN llm_providers p ON c.provider_id = p.id
            LEFT JOIN models m ON c.model_id = m.id
        """))
        configs = configs_result.fetchall()

        result = {
            'llmConfigs': []
        }

        for config in configs:
            result['llmConfigs'].append({
                'id': config[0],
                'llm_name': config[1],  # Use connection name for backward compatibility
                'base_url': config[2],
                'model_name': config[3] or 'default',
                'provider_type': config[4],
                'port_no': config[5],
                'api_key': config[6]
            })

        session.close()
        return jsonify(result)
    except Exception as e:
        print(f"Error getting connections (LLM configurations): {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/prompts', methods=['GET'])
def get_prompts():
    """Get all prompts from the database"""
    try:
        session = Session()
        prompts = session.query(Prompt).all()

        result = {
            'prompts': []
        }

        for prompt in prompts:
            result['prompts'].append({
                'id': prompt.id,
                'prompt_text': prompt.prompt_text,
                'description': prompt.description,
                'active': bool(prompt.active)  # Include active field as boolean
            })

        session.close()
        return jsonify(result)
    except Exception as e:
        print(f"Error getting prompts: {e}")
        return jsonify({'error': str(e)}), 500

# Add legacy provider endpoints for frontend compatibility
@app.route('/providers', methods=['GET'])
def get_providers_legacy():
    """Legacy endpoint - returns provider data directly"""
    try:
        from services.llm_provider_service import llm_provider_service
        providers = llm_provider_service.get_all_providers()
        return jsonify({
            'success': True,
            'providers': providers
        }), 200
    except Exception as e:
        print(f"Error getting providers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/api/providers', methods=['GET'])
def get_providers_api():
    """Alternative API endpoint for providers"""
    try:
        from services.llm_provider_service import llm_provider_service
        providers = llm_provider_service.get_all_providers()
        return jsonify({
            'success': True,
            'providers': providers
        }), 200
    except Exception as e:
        print(f"Error getting providers: {e}")
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

# Removed duplicate /api/llm-configurations endpoint - now handled by service_routes.py
# Removed duplicate /api/folders endpoint - now handled by service_routes.py

@app.route('/api/progress', methods=['GET'])
def get_progress():
    """Get current processing progress - LLM responses moved to KnowledgeDocuments database"""
    try:
        session = Session()

        # Count total documents in current database
        total_documents = session.query(Document).count()

        session.close()

        # Since LLM responses are now in KnowledgeDocuments database, return basic info
        return jsonify({
            'totalDocuments': total_documents,
            'processedDocuments': 0,  # Would need to query KnowledgeDocuments database
            'outstandingDocuments': 0,  # Would need to query KnowledgeDocuments database
            'progress': 0,
            'message': 'LLM responses moved to KnowledgeDocuments database'
        })
    except Exception as e:
        print(f"Error getting progress: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/errors', methods=['GET'])
def get_errors():
    """Get a list of processing errors - LLM responses moved to KnowledgeDocuments database"""
    try:
        # Since LLM responses are now in KnowledgeDocuments database, return empty list
        return jsonify({
            'errors': [],
            'message': 'LLM responses moved to KnowledgeDocuments database'
        })
    except Exception as e:
        print(f"Error getting errors: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/folders/preprocess', methods=['POST'])
def preprocess_folder():
    """Start folder preprocessing workflow"""
    try:
        data = request.get_json()

        if not data:
            return jsonify({'error': 'JSON data required'}), 400

        folder_path = data.get('folder_path')
        folder_name = data.get('folder_name')

        if not folder_path:
            return jsonify({'error': 'folder_path is required'}), 400

        if not folder_name:
            return jsonify({'error': 'folder_name is required'}), 400

        # Validate folder exists
        import os
        if not os.path.exists(folder_path):
            return jsonify({'error': f'Folder does not exist: {folder_path}'}), 400

        if not os.path.isdir(folder_path):
            return jsonify({'error': f'Path is not a directory: {folder_path}'}), 400

        # Use the actual FolderPreprocessingService
        from services.folder_preprocessing_service import FolderPreprocessingService
        import uuid
        import threading

        task_id = str(uuid.uuid4())

        # Initialize task tracking
        if not hasattr(app, 'preprocessing_tasks'):
            app.preprocessing_tasks = {}

        app.preprocessing_tasks[task_id] = {
            'status': 'STARTED',
            'folder_path': folder_path,
            'folder_name': folder_name,
            'progress': 0,
            'total_files': 0,
            'processed_files': 0,
            'valid_files': 0,
            'invalid_files': 0,
            'error': None,
            'folder_id': None
        }

        # Start preprocessing in background thread
        def run_preprocessing():
            try:
                service = FolderPreprocessingService()
                with app.app_context():
                    result = service.preprocess_folder_async(folder_path, folder_name, task_id)
                    app.preprocessing_tasks[task_id].update({
                        'status': 'COMPLETED',
                        'progress': 100,
                        'folder_id': result.get('folder_id')
                    })
            except Exception as e:
                app.preprocessing_tasks[task_id].update({
                    'status': 'ERROR',
                    'error': str(e)
                })

        thread = threading.Thread(target=run_preprocessing)
        thread.daemon = True
        thread.start()

        return jsonify({
            'message': 'Folder preprocessing started',
            'task_id': task_id
        }), 202

    except Exception as e:
        print(f"Error preprocessing folder: {e}")
        return jsonify({'error': f'Preprocessing failed: {str(e)}'}), 500

@app.route('/api/folders/<int:folder_id>/status', methods=['GET'])
def get_folder_status(folder_id):
    """Get folder preprocessing status and statistics"""
    try:
        from services.folder_preprocessing_service import FolderPreprocessingService

        service = FolderPreprocessingService()
        status = service.get_folder_status(folder_id)

        if not status:
            return jsonify({'error': 'Folder not found'}), 404

        return jsonify({
            'folder_status': status
        }), 200

    except Exception as e:
        print(f"Error getting folder status: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/folders/task/<task_id>/status', methods=['GET'])
def get_task_status(task_id):
    """Get preprocessing task status"""
    try:
        # Check if task exists in our tracking
        if not hasattr(app, 'preprocessing_tasks') or task_id not in app.preprocessing_tasks:
            return jsonify({'error': 'Task not found'}), 404

        task_info = app.preprocessing_tasks[task_id]

        return jsonify(task_info), 200

    except Exception as e:
        print(f"Error getting task status: {e}")
        return jsonify({'error': str(e)}), 500

# Initialize service integration components
def initialize_services():
    """Initialize all background services"""
    try:
        from services.health_monitor import health_monitor
        from api.status_polling import polling_service
        from services.startup_recovery import perform_startup_recovery

        # Perform startup recovery FIRST
        logger.info("=" * 60)
        logger.info("PERFORMING STARTUP RECOVERY")
        logger.info("=" * 60)
        try:
            from services.simple_recovery import perform_simple_recovery
            recovery_result = perform_simple_recovery()
            logger.info(f"Startup recovery completed: {recovery_result}")
        except Exception as e:
            logger.error(f"Recovery failed but continuing: {e}")

        # Start health monitoring
        health_monitor.start_monitoring()
        logger.info("Service health monitoring started")

        # Start status polling service
        polling_service.start_polling()
        logger.info("Status polling service initialized and started")

        # Start batch queue processor
        logger.info("Starting batch queue processor...")
        from services.batch_queue_processor import start_queue_processor
        start_queue_processor()
        logger.info("Batch queue processor started")

    except Exception as e:
        logger.error(f"Error initializing services: {e}")

if __name__ == '__main__':
    try:
        # Initialize all services
        initialize_services()

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
        sys.exit(1)
