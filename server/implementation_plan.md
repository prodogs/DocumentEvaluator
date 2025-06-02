# Implementation Plan for Document Evaluator Service

This document outlines the detailed implementation plan to fix the Document Evaluator service running on port 5001.

## 1. Fix Critical Issues

### 1.1. Fix the `executor` Reference in app_launcher.py

The app_launcher.py file references an undefined `executor` variable in the finally block. We need to add the missing definition:

```python
# Add at the top of the file with other imports
from concurrent.futures import ThreadPoolExecutor

# Add before the main function
executor = ThreadPoolExecutor(max_workers=10)

# The finally block can remain unchanged
```

### 1.2. Implement Missing API Endpoints

The frontend is trying to call two endpoints that are defined in openapi.json but not implemented in the code:
- `/analyze_document_with_llm`
- `/analyze_status/{task_id}`

Create a new file `server/api/document_routes.py` with the following content:

```python
import os
import uuid
import time
import threading
from flask import Blueprint, request, jsonify
from werkzeug.utils import secure_filename
from sqlalchemy.sql import func

from server.models import Document, LlmConfiguration, Prompt, LlmResponse
from server.database import Session

document_routes = Blueprint('document_routes', __name__)

# Store background tasks with their status
background_tasks = {}

@document_routes.route('/analyze_document_with_llm', methods=['POST'])
def analyze_document_with_llm():
    """Analyze uploaded documents with LLM providers"""
    try:
        # Check if files were uploaded
        if 'files' not in request.files:
            return jsonify({
                'message': 'No files uploaded',
                'totalFiles': 0
            }), 400
        
        files = request.files.getlist('files')
        if not files or files[0].filename == '':
            return jsonify({
                'message': 'No files selected',
                'totalFiles': 0
            }), 400
        
        # Generate a unique task ID
        task_id = str(uuid.uuid4())
        
        # Initialize task status
        background_tasks[task_id] = {
            'status': 'STARTED',
            'progress': 0,
            'total_files': len(files),
            'processed_files': 0,
            'error': None
        }
        
        # Save files to a temporary location
        saved_files = []
        for file in files:
            # Create a safe filename
            filename = secure_filename(file.filename)
            # Create a temporary directory if it doesn't exist
            os.makedirs('temp_uploads', exist_ok=True)
            # Save the file
            file_path = os.path.join('temp_uploads', filename)
            file.save(file_path)
            saved_files.append(file_path)
        
        # Start processing in background
        def process_files_background():
            try:
                session = Session()
                
                # Get LLM configurations and prompts
                llm_configs = session.query(LlmConfiguration).all()
                prompts = session.query(Prompt).all()
                
                if not llm_configs:
                    background_tasks[task_id]['status'] = 'ERROR'
                    background_tasks[task_id]['error'] = 'No LLM configurations found'
                    return
                
                if not prompts:
                    background_tasks[task_id]['status'] = 'ERROR'
                    background_tasks[task_id]['error'] = 'No prompts found'
                    return
                
                # Process each file with each LLM configuration and prompt
                total_combinations = len(saved_files) * len(llm_configs) * len(prompts)
                background_tasks[task_id]['total_files'] = total_combinations
                
                processed_count = 0
                for file_path in saved_files:
                    # Store document in database
                    filepath, filename = os.path.split(file_path)
                    document = Document(filepath=filepath, filename=filename)
                    session.add(document)
                    session.commit()
                    
                    for llm_config in llm_configs:
                        for prompt in prompts:
                            # Create LLM response record
                            llm_response = LlmResponse(
                                document_id=document.id,
                                prompt_id=prompt.id,
                                llm_name=llm_config.llm_name,
                                task_id=task_id,
                                status='P',  # Processing
                                started_processing_at=func.now()
                            )
                            session.add(llm_response)
                            session.commit()
                            
                            try:
                                # TODO: Implement actual LLM processing logic here
                                # This would involve:
                                # 1. Extracting text from the document
                                # 2. Sending the text to the LLM provider
                                # 3. Storing the response
                                
                                # For now, simulate processing
                                time.sleep(1)
                                
                                # Update response record
                                llm_response.status = 'S'  # Success
                                llm_response.completed_processing_at = func.now()
                                llm_response.response_text = "Sample response"
                                llm_response.response_time_ms = 1000
                                session.commit()
                            except Exception as e:
                                # Update response record with error
                                llm_response.status = 'F'  # Failure
                                llm_response.completed_processing_at = func.now()
                                llm_response.error_message = str(e)
                                session.commit()
                            
                            processed_count += 1
                            background_tasks[task_id]['processed_files'] = processed_count
                            background_tasks[task_id]['progress'] = int((processed_count / total_combinations) * 100)
                
                # Update final status
                background_tasks[task_id]['status'] = 'COMPLETED'
                background_tasks[task_id]['progress'] = 100
                
                session.close()
            except Exception as e:
                if task_id in background_tasks:
                    background_tasks[task_id]['status'] = 'ERROR'
                    background_tasks[task_id]['error'] = str(e)
                if 'session' in locals():
                    session.close()
        
        # Start the background thread
        thread = threading.Thread(target=process_files_background)
        thread.daemon = True
        thread.start()
        
        return jsonify({
            'message': f'Started processing {len(files)} files',
            'totalFiles': len(files),
            'task_id': task_id
        }), 200
    
    except Exception as e:
        print(f"Error processing files: {e}")
        import traceback
        traceback.print_exc()
        return jsonify({
            'message': 'Failed to process files',
            'error': str(e)
        }), 500

@document_routes.route('/analyze_status/<task_id>', methods=['GET'])
def analyze_status(task_id):
    """Get the status of a document analysis task"""
    try:
        # Check if task exists
        if task_id not in background_tasks:
            return jsonify({
                'status': 'NOT_FOUND',
                'totalDocuments': 0,
                'processedDocuments': 0,
                'outstandingDocuments': 0,
                'error_message': 'Task not found'
            }), 404
        
        task_info = background_tasks[task_id]
        
        # Get counts from database
        session = Session()
        total_documents = task_info.get('total_files', 0)
        processed_documents = task_info.get('processed_files', 0)
        outstanding_documents = total_documents - processed_documents
        
        # Check for errors
        error_message = task_info.get('error')
        
        session.close()
        
        return jsonify({
            'status': task_info.get('status', 'UNKNOWN'),
            'totalDocuments': total_documents,
            'processedDocuments': processed_documents,
            'outstandingDocuments': outstanding_documents,
            'progress': task_info.get('progress', 0),
            'error_message': error_message
        })
    
    except Exception as e:
        print(f"Error getting task status: {e}")
        return jsonify({
            'status': 'ERROR',
            'error_message': str(e)
        }), 500

def register_document_routes(app):
    """Register document routes with the Flask app"""
    app.register_blueprint(document_routes)
    
    # Make background_tasks available globally
    app.config['BACKGROUND_TASKS'] = background_tasks
    
    return app
### 1.3. Create Process Folder Function

Create a new file `server/api/process_folder.py` with the following content:

```python
import os
import time
from server.models import Document, LlmConfiguration, Prompt, LlmResponse
from server.database import Session
from sqlalchemy.sql import func

def traverse_directory(path, supported_extensions=None):
    """
    Recursively traverse a directory and return a list of supported files.
    
    Args:
        path (str): Path to the directory to traverse
        supported_extensions (list): List of supported file extensions (default: document types)
        
    Returns:
        list: List of file paths that match the supported extensions
    """
    if supported_extensions is None:
        # Default supported document extensions
        supported_extensions = {'.pdf', '.txt', '.docx', '.xlsx', '.doc', '.xls', '.rtf', '.odt', '.ods', '.md'}
    else:
        # Ensure extensions are in lowercase and start with a dot
        supported_extensions = {ext.lower() if ext.startswith('.') else f'.{ext.lower()}'
                                for ext in supported_extensions}
    
    files = []
    
    try:
        # Check if the folder path exists
        if not os.path.exists(path):
            raise FileNotFoundError(f"Directory not found: {path}")
        
        if not os.path.isdir(path):
            raise NotADirectoryError(f"Path is not a directory: {path}")
        
        # Walk through all subdirectories
        for root, directories, filenames in os.walk(path):
            for filename in filenames:
                # Get the file extension in lowercase
                file_extension = os.path.splitext(filename)[1].lower()
                
                # Check if the file extension is supported
                if file_extension in supported_extensions:
                    file_path = os.path.join(root, filename)
                    
                    # Verify file exists and is readable
                    if os.path.isfile(file_path) and os.access(file_path, os.R_OK):
                        files.append(file_path)
        
    except PermissionError as e:
        print(f"Permission denied accessing directory: {path}")
        raise PermissionError(f"Permission denied accessing directory: {path}") from e
    except Exception as e:
        print(f"Error traversing directory {path}: {str(e)}")
        raise
    
    return files

def process_folder(folder_path, task_id=None):
    """Process all files in a folder
    
    Args:
        folder_path (str): Path to the folder to process
        task_id (str, optional): Task ID for tracking progress
        
    Returns:
        dict: Result of processing with totalFiles and processedFiles counts
    """
    try:
        # Get all supported files in the folder
        files = traverse_directory(folder_path)
        
        if not files:
            return {
                'totalFiles': 0,
                'processedFiles': 0,
                'message': f'No supported files found in folder: {folder_path}'
            }
        
        # Get LLM configurations and prompts
        session = Session()
        llm_configs = session.query(LlmConfiguration).all()
        prompts = session.query(Prompt).all()
        
        if not llm_configs:
            session.close()
            return {
                'totalFiles': len(files),
                'processedFiles': 0,
                'message': 'No LLM configurations found'
            }
        
        if not prompts:
            session.close()
            return {
                'totalFiles': len(files),
                'processedFiles': 0,
                'message': 'No prompts found'
            }
        
        # Process each file
        processed_count = 0
        for file_path in files:
            # Check if document already exists in database
            filepath, filename = os.path.split(file_path)
            existing_doc = session.query(Document).filter_by(filepath=filepath, filename=filename).first()
            
            if not existing_doc:
                # Create new document record
                document = Document(filepath=filepath, filename=filename)
                session.add(document)
                session.commit()
                doc_id = document.id
            else:
                doc_id = existing_doc.id
            
            # Process with each LLM configuration and prompt
            for llm_config in llm_configs:
                for prompt in prompts:
                    # Check if this combination has already been processed
                    existing_response = session.query(LlmResponse).filter_by(
                        document_id=doc_id,
                        prompt_id=prompt.id,
                        llm_name=llm_config.llm_name
                    ).first()
                    
                    if existing_response and existing_response.status in ['S', 'F']:
                        # Already processed, skip
                        processed_count += 1
                        continue
                    
                    # Create or update LLM response record
                    if not existing_response:
                        llm_response = LlmResponse(
                            document_id=doc_id,
                            prompt_id=prompt.id,
                            llm_name=llm_config.llm_name,
                            task_id=task_id,
                            status='P',  # Processing
                            started_processing_at=func.now()
                        )
                        session.add(llm_response)
                    else:
                        llm_response = existing_response
                        llm_response.status = 'P'  # Processing
                        llm_response.started_processing_at = func.now()
                        llm_response.task_id = task_id
                    
                    session.commit()
                    
                    try:
                        # TODO: Implement actual LLM processing logic here
                        # This would involve:
                        # 1. Extracting text from the document
                        # 2. Sending the text to the LLM provider
                        # 3. Storing the response
                        
                        # For now, simulate processing
                        time.sleep(1)
                        
                        # Update response record
                        llm_response.status = 'S'  # Success
                        llm_response.completed_processing_at = func.now()
                        llm_response.response_text = "Sample response"
                        llm_response.response_time_ms = 1000
                        session.commit()
                    except Exception as e:
                        # Update response record with error
                        llm_response.status = 'F'  # Failure
                        llm_response.completed_processing_at = func.now()
                        llm_response.error_message = str(e)
                        session.commit()
                    
                    processed_count += 1
        
        session.close()
        
        return {
            'totalFiles': len(files) * len(llm_configs) * len(prompts),
            'processedFiles': processed_count,
            'message': f'Processed {processed_count} file-LLM-prompt combinations'
        }
    
    except Exception as e:
        print(f"Error processing folder {folder_path}: {e}")
        import traceback
        traceback.print_exc()
        if 'session' in locals():
            session.close()
        
        return {
            'totalFiles': 0,
            'processedFiles': 0,
            'error': str(e)
        }
```

### 1.4. Update app.py

Modify app.py to fix the duplicate imports and properly use the functions:

```python
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

from server.database import Session
from server.models import Folder, LlmConfiguration, Prompt, LlmResponse, Document
from server.api.document_routes import register_document_routes
from server.api.process_folder import process_folder

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all origins

# Register document routes
register_document_routes(app)

# Add route to serve the landing page
@app.route('/')
def index():
    return app.send_static_file('index.html')

# Store background tasks with their status
background_tasks = {}

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
    """Get all LLM configurations from the database"""
    try:
        session = Session()
        llm_configs = session.query(LlmConfiguration).all()

        result = {
            'llmConfigs': []
        }

        for config in llm_configs:
            result['llmConfigs'].append({
                'id': config.id,
                'llm_name': config.llm_name,
                'base_url': config.base_url,
                'model_name': config.model_name,
                'api_key': config.api_key,
                'provider_type': config.provider_type,
                'port_no': config.port_no
            })

        session.close()
        return jsonify(result)
    except Exception as e:
        print(f"Error getting LLM configurations: {e}")
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
                'description': prompt.description
            })

        session.close()
        return jsonify(result)
    except Exception as e:
        print(f"Error getting prompts: {e}")
        return jsonify({'error': str(e)}), 500

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
```

### 1.5. Update app_launcher.py

Modify app_launcher.py to fix the executor reference:

```python
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
from app import app

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
        logger.info("Thread resources cleaned up.")

    return 0

if __name__ == '__main__':
    sys.exit(main())
```

### 1.6. Update routes.py

Modify routes.py to use the process_folder function:

```python
from flask import jsonify, request
import uuid
import threading

# Import from models and database
from server.models import Folder, Document, LlmConfiguration, Prompt, LlmResponse
from server.database import Session
from server.api.process_folder import process_folder

def register_routes(app, background_tasks, process_folder_func=None):
    """Register all routes for the application

    Args:
        app: Flask application instance
        background_tasks: Dictionary to store background task status
        process_folder_func: Function to process a folder (optional)
    """
    
    # Use the provided process_folder_func or the imported process_folder
    process_folder_func = process_folder_func or process_folder

    # Process DB Folders endpoint
    @app.route('/process-db-folders', methods=['POST'])
    def process_db_folders():
        """Process all files in folders stored in the database"""
        try:
            print("Process-db-folders endpoint called")
            # Get all folders from the database
            session = Session()
            folders = session.query(Folder).all()
            session.close()

            if not folders:
                return jsonify({
                    'message': 'No folders found in the database. Please add folders first.',
                    'totalFiles': 0
                }), 200

            # Generate a unique task ID
            task_id = str(uuid.uuid4())

            # Initialize task status
            background_tasks[task_id] = {
                'status': 'STARTED',
                'progress': 0,
                'total_files': 0,
                'processed_files': 0,
                'error': None
            }

            # Count total files to be processed
            session = Session()
            llm_configs_count = session.query(LlmConfiguration).count()
            prompts_count = session.query(Prompt).count()
            docs_count = session.query(Document).count()
            session.close()

            # Start processing in background
            def background_processing():
                try:
                    total_files = 0
                    processed_files = 0

                    for folder in folders:
                        print(f"Processing folder: {folder.path}")
                        try:
                            # Process folder and get result
                            result = process_folder_func(folder.path, task_id=task_id)

                            # Update counts
                            total_files += result.get('totalFiles', 0)
                            processed_files += result.get('processedFiles', 0)
                        except Exception as e:
                            print(f"Error processing folder {folder.path}: {e}")
                            if task_id in background_tasks:
                                background_tasks[task_id]['error'] = str(e)

                    # Update final status
                    if task_id in background_tasks:
                        background_tasks[task_id]['status'] = 'COMPLETED'
                        background_tasks[task_id]['progress'] = 100
                        background_tasks[task_id]['total_files'] = total_files
                        background_tasks[task_id]['processed_files'] = processed_files

                    print(f"Completed processing {processed_files} out of {total_files} files from database folders")
                except Exception as e:
                    print(f"Error in background processing: {e}")
                    if task_id in background_tasks:
                        background_tasks[task_id]['status'] = 'ERROR'
                        background_tasks[task_id]['error'] = str(e)

            # Start the background thread
            thread = threading.Thread(target=background_processing)
            thread.daemon = True
            thread.start()

            # Estimate total combinations
            total_combinations = docs_count * llm_configs_count * prompts_count

            # Update initial task status with estimated total
            background_tasks[task_id]['total_files'] = total_combinations

            return jsonify({
                'task_id': task_id,
                'message': f"Started processing files from {len(folders)} database folders with {llm_configs_count} LLM configurations and {prompts_count} prompts",
                'totalFiles': total_combinations
            }), 200

        except Exception as e:
            print(f"Error processing database folders: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'message': 'Failed to process database folders.',
                'error': str(e)
            }), 500

    # Add additional routes here
    # ...

    return app
```

## 2. Implementation Order

1. Fix the `executor` reference in app_launcher.py
2. Create the process_folder.py file
3. Create the document_routes.py file
4. Update app.py to remove duplicate code and fix imports
5. Update routes.py to use the new process_folder function
6. Update app_launcher.py to register all routes

## 3. Testing Plan

After implementing the changes, we should test the service to ensure it's working correctly:

1. Start the service using the launch_service.sh script
2. Test the health endpoint: `curl http://localhost:5001/api/health`
3. Test the process-db-folders endpoint: `curl -X POST http://localhost:5001/process-db-folders`
4. Test the analyze_document_with_llm endpoint by uploading a file
5. Test the analyze_status endpoint with the returned task ID
6. Verify that the frontend can connect to the backend

## 4. Next Steps

After fixing the service on port 5001, we should:

1. Update the client code to properly handle the responses from the backend
2. Implement proper error handling and logging
3. Add more comprehensive tests
4. Document the API endpoints and their usage