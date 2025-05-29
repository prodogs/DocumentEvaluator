import threading
import uuid
from flask import jsonify
from sqlalchemy.orm import Session

from server.app import Folder
import server.app as main_app
from server.models import LlmConfiguration, Prompt


def register_db_folders_endpoints(app):
    """Register the /api/process-db-folders endpoint

    Args:
        app: Flask application instance
    """
    # Import models inside the function to avoid circular imports


    @app.route('/api/process-db-folders', methods=['POST'])
    def api_process_db_folders():
        """API endpoint to process all files in folders stored in the database"""
        try:
            print("API process-db-folders endpoint called")

            # Get only active folders from the database
            session = Session()
            folders = session.query(Folder).filter(Folder.active == 1).all()
            session.close()

            if not folders:
                return jsonify({
                    'message': 'No active folders found in the database. Please add folders first or activate existing folders.',
                    'totalFiles': 0
                }), 200

            # Generate a unique task ID
            task_id = str(uuid.uuid4())

            # Initialize task status
            if hasattr(main_app, 'background_tasks'):
                main_app.background_tasks[task_id] = {
                    'status': 'STARTED',
                    'progress': 0,
                    'total_files': 0,
                    'processed_files': 0,
                    'error': None
                }

            # Start processing in background
            def background_processing():
                try:
                    total_files = 0
                    processed_files = 0

                    for folder in folders:
                        print(f"Processing folder from API endpoint: {folder.folder_path}")
                        try:
                            # Process folder and get result using the main app's process_folder function
                            if hasattr(main_app, 'process_folder'):
                                result = main_app.process_folder(folder.folder_path, task_id=task_id)

                                # Update counts
                                total_files += result.get('totalFiles', 0)
                                processed_files += result.get('processedFiles', 0)
                            else:
                                print("Error: process_folder function not found in main app module")
                        except Exception as e:
                            print(f"Error processing folder {folder.folder_path}: {e}")
                            if hasattr(main_app, 'background_tasks') and task_id in main_app.background_tasks:
                                main_app.background_tasks[task_id]['error'] = str(e)

                    # Update final status
                    if hasattr(main_app, 'background_tasks') and task_id in main_app.background_tasks:
                        main_app.background_tasks[task_id]['status'] = 'COMPLETED'
                        main_app.background_tasks[task_id]['progress'] = 100
                        main_app.background_tasks[task_id]['total_files'] = total_files
                        main_app.background_tasks[task_id]['processed_files'] = processed_files

                    print(f"Completed processing {processed_files} out of {total_files} files from database folders")
                except Exception as e:
                    print(f"Error in API background processing: {e}")
                    if hasattr(main_app, 'background_tasks') and task_id in main_app.background_tasks:
                        main_app.background_tasks[task_id]['status'] = 'ERROR'
                        main_app.background_tasks[task_id]['error'] = str(e)

            # Start the background thread
            thread = threading.Thread(target=background_processing)
            thread.daemon = True
            thread.start()

            # Count total files to be processed
            session = Session()
            llm_configs_count = session.query(LlmConfiguration).count()
            prompts_count = session.query(Prompt).count()
            docs_count = session.query(main_app.Document).count()
            session.close()

            # Estimate total combinations
            total_combinations = docs_count * llm_configs_count * prompts_count

            # Update initial task status with estimated total
            if hasattr(main_app, 'background_tasks') and task_id in main_app.background_tasks:
                main_app.background_tasks[task_id]['total_files'] = total_combinations

            return jsonify({
                'task_id': task_id,
                'message': f"Started processing files from {len(folders)} database folders with {llm_configs_count} LLM configurations and {prompts_count} prompts",
                'totalFiles': total_combinations
            }), 200

        except Exception as e:
            print(f"Error in API process_db_folders: {e}")
            import traceback
            traceback.print_exc()
            return jsonify({
                'message': 'Failed to process database folders.',
                'error': str(e)
            }), 500

    print("Successfully registered API endpoints for process_db_folders")
    return app