import os
import json
import time
import mimetypes
import datetime
import logging
from flask import Flask, request, jsonify
from flask_swagger_ui import get_swaggerui_blueprint
from flask_cors import CORS
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, inspect, text
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship
from sqlalchemy.sql import func
from dotenv import load_dotenv
import requests
import uuid
import pathlib

from database import Session
from models import Folder, Prompt, LlmResponse, Document
from api.document_routes import register_document_routes, background_tasks
from api.process_folder import process_folder
from api.status_polling import polling_service
from api.run_batch import run_batch_bp

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all origins

# Register document routes
register_document_routes(app)

# Register batch execution routes
app.register_blueprint(run_batch_bp)

# Register service routes - this will be done in app_launcher.py to avoid duplicate registration
# from api.service_routes import service_routes
# app.register_blueprint(service_routes)

# Register folder routes - this will be done in app_launcher.py to avoid duplicate registration
# from api.folder_routes import folder_routes
# app.register_blueprint(folder_routes)

# Register folder preprocessing routes - this will be done in app_launcher.py to avoid duplicate registration
# from api.folder_preprocessing_routes import folder_preprocessing_bp
# app.register_blueprint(folder_preprocessing_bp)

# Register batch routes - this will be done in app_launcher.py to avoid duplicate registration
# from api.batch_routes import register_batch_routes
# register_batch_routes(app)

# Register LLM provider routes - this will be done in app_launcher.py to avoid duplicate registration
# from api.llm_provider_routes import llm_provider_bp
# app.register_blueprint(llm_provider_bp)

# Register model routes - this will be done in app_launcher.py to avoid duplicate registration
# from api.model_routes import model_bp
# app.register_blueprint(model_bp)

# Register main routes - this will be done in app_launcher.py to avoid duplicate registration
# from server.routes import register_routes
# register_routes(app, background_tasks)

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
    """Get current processing progress"""
    try:
        session = Session()

        # Count total documents
        total_documents = session.query(LlmResponse).count()

        # Count processed documents (status S or F)
        processed_documents = session.query(LlmResponse).filter(
            LlmResponse.status.in_(['S', 'F'])
        ).count()

        # Count outstanding documents (status P or R)
        outstanding_documents = session.query(LlmResponse).filter(
            LlmResponse.status.in_(['P', 'R'])
        ).count()

        # Calculate progress percentage
        progress = 0
        if total_documents > 0:
            progress = int((processed_documents / total_documents) * 100)

        session.close()

        return jsonify({
            'totalDocuments': total_documents,
            'processedDocuments': processed_documents,
            'outstandingDocuments': outstanding_documents,
            'progress': progress
        })
    except Exception as e:
        print(f"Error getting progress: {e}")
        return jsonify({'error': str(e)}), 500

@app.route('/api/errors', methods=['GET'])
def get_errors():
    """Get a list of processing errors"""
    try:
        session = Session()

        # Get all responses with status F (failed)
        error_responses = session.query(LlmResponse).filter(LlmResponse.status == 'F').all()

        errors = []
        for response in error_responses:
            # Get associated document and prompt
            document = session.query(Document).filter(Document.id == response.document_id).first()
            prompt = session.query(Prompt).filter(Prompt.id == response.prompt_id).first()

            if document and prompt:
                errors.append({
                    'filename': document.filename,
                    'llm_name': response.llm_name,
                    'prompt_text': prompt.prompt_text,
                    'error_message': response.error_message,
                    'timestamp': response.timestamp.isoformat() if response.timestamp else None
                })

        session.close()

        return jsonify({
            'errors': errors
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

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)
