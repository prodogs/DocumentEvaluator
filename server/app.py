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

from .database import Session
from server.models import Folder, LlmConfiguration, Prompt, LlmResponse, Document
from server.api.document_routes import register_document_routes, background_tasks
from server.api.process_folder import process_folder
from server.api.status_polling import polling_service
from server.api.run_batch import run_batch_bp

load_dotenv()  # Load environment variables from .env file

app = Flask(__name__, static_folder='static')
CORS(app)  # Enable CORS for all origins

# Register document routes
register_document_routes(app)

# Register batch execution routes
app.register_blueprint(run_batch_bp)

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
