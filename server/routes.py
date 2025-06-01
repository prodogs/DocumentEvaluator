import logging
from flask import jsonify, request
import uuid
import threading

# Import from models and database
from models import Folder, Document, Connection, Prompt, LlmResponse
from database import Session
from api.process_folder import process_folder
from services.batch_service import batch_service

logger = logging.getLogger(__name__)

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
            logger.info("Process-db-folders endpoint called")

            # Get batch_name, meta_data, and folder_ids from request body if provided
            batch_name = None
            meta_data = None
            folder_ids = None
            if request.is_json:
                data = request.get_json()
                batch_name = data.get('batch_name') if data else None
                meta_data = data.get('meta_data') if data else None
                folder_ids = data.get('folder_ids') if data else None

            logger.info(f"Batch name: {batch_name}")
            logger.info(f"Meta data: {meta_data}")
            logger.info(f"Folder IDs: {folder_ids}")

            # Get folders from the database
            session = Session()
            if folder_ids:
                # Use specific folder IDs provided in request
                folders = session.query(Folder).filter(Folder.id.in_(folder_ids)).all()
                logger.info(f"Using specific folder IDs: {folder_ids}")
            else:
                # Fallback to all active folders (legacy behavior)
                folders = session.query(Folder).filter(Folder.active == 1).all()
                logger.info("Using all active folders (legacy mode)")
            session.close()

            logger.info(f"Found {len(folders)} active folders in the database.")

            if not folders:
                if folder_ids:
                    logger.info(f"No folders found for the specified IDs: {folder_ids}")
                    return jsonify({
                        'message': f'No folders found for the specified IDs: {folder_ids}. Please check your folder selection.',
                        'totalFiles': 0,
                        'task_id': None
                    }), 400
                else:
                    logger.info("No active folders found in the database. Returning early.")
                    return jsonify({
                        'message': 'No active folders found in the database. Please add folders first or activate existing folders.',
                        'totalFiles': 0,
                        'task_id': None  # Explicitly set task_id to None for clarity
                    }), 400  # Changed to 400 since this is an error condition

            # Generate a unique task ID
            task_id = str(uuid.uuid4())
            logger.info(f"Generated task ID: {task_id}")

            # Initialize task status
            background_tasks[task_id] = {
                'status': 'STARTED',
                'progress': 0,
                'total_files': 0,
                'processed_files': 0,
                'error': None
            }
            logger.info(f"Initialized task status for task ID {task_id}")

            # Count total files to be processed
            session = Session()
            llm_configs_count = session.query(Connection).filter(Connection.is_active == True).count()
            prompts_count = session.query(Prompt).count()
            docs_count = session.query(Document).count()
            session.close()
            logger.info(f"LLM configs count: {llm_configs_count}, Prompts count: {prompts_count}, Documents count: {docs_count}")

            # Start processing in background
            def background_processing():
                session = Session() # Create a new session for the background thread
                try:
                    total_files = 0
                    processed_files = 0
                    logger.info(f"Background processing started for task ID: {task_id}")

                    # Create a single batch for all folders
                    folder_ids = [folder.id for folder in folders]
                    batch_data = batch_service.create_multi_folder_batch(
                        folder_ids=folder_ids,
                        batch_name=batch_name,
                        description=f"Multi-folder processing batch for {len(folders)} folders",
                        meta_data=meta_data
                    )
                    batch_id = batch_data['id']
                    logger.info(f"Created multi-folder batch #{batch_data['batch_number']} with ID {batch_id} for folders: {folder_ids}")

                    for folder in folders:
                        logger.info(f"Processing folder: {folder.folder_path} for task ID: {task_id}")
                        try:
                            # Process folder and get result with batch_id (shared across all folders)
                            result = process_folder_func(
                                folder.folder_path,
                                task_id=task_id,
                                batch_name=batch_data['batch_name'],
                                folder_id=folder.id,  # Pass the folder ID for proper linking
                                batch_id=batch_id  # Pass the shared batch ID
                            )
                            logger.info(f"Result from processing folder {folder.folder_path}: {result}")

                            # Update counts
                            total_files += result.get('totalFiles', 0)
                            processed_files += result.get('processedFiles', 0)
                        except Exception as e:
                            logger.error(f"Error processing folder {folder.folder_path} for task ID {task_id}: {e}", exc_info=True)
                            if task_id in background_tasks:
                                background_tasks[task_id]['error'] = str(e)

                    # Update final status
                    if task_id in background_tasks:
                        background_tasks[task_id]['status'] = 'COMPLETED'
                        background_tasks[task_id]['progress'] = 100
                        background_tasks[task_id]['total_files'] = total_files
                        background_tasks[task_id]['processed_files'] = processed_files
                        logger.info(f"Background processing completed for task ID {task_id}. Processed {processed_files} out of {total_files} files.")

                except Exception as e:
                    logger.error(f"Error in background processing for task ID {task_id}: {e}", exc_info=True)
                    if task_id in background_tasks:
                        background_tasks[task_id]['status'] = 'ERROR'
                        background_tasks[task_id]['error'] = str(e)
                finally:
                    session.close() # Ensure the session is closed

            # Start the background thread
            thread = threading.Thread(target=background_processing)
            thread.daemon = True
            thread.start()
            logger.info(f"Background thread started for task ID: {task_id}")

            # Estimate total combinations
            total_combinations = docs_count * llm_configs_count * prompts_count
            logger.info(f"Estimated total combinations: {total_combinations}")

            # Update initial task status with estimated total
            background_tasks[task_id]['total_files'] = total_combinations

            response_message = f"Started processing files from {len(folders)} database folders with {llm_configs_count} LLM configurations and {prompts_count} prompts"
            logger.info(f"Returning response for task ID {task_id}: {response_message}")
            return jsonify({
                'task_id': task_id,
                'message': response_message,
                'totalFiles': total_combinations
            }), 200

        except Exception as e:
            logger.error(f"Error processing database folders: {e}", exc_info=True)
            return jsonify({
                'message': 'Failed to process database folders.',
                'error': str(e)
            }), 500

    # Add additional routes here
    # ...

    return app
