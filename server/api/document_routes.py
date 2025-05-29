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
        # Validate task_id
        if not task_id or task_id in ['null', 'undefined', 'None']:
            print(f"Invalid task ID received: '{task_id}'")
            return jsonify({
                'status': 'INVALID_TASK_ID',
                'totalDocuments': 0,
                'processedDocuments': 0,
                'outstandingDocuments': 0,
                'error_message': 'Invalid task ID provided'
            }), 400

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