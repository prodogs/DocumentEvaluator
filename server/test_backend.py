import requests
import json
import os
import time
import sqlite3
from pathlib import Path
from dotenv import load_dotenv
from typing import List

load_dotenv() # Load environment variables from .env file

RAG_API_BASE_URL = os.getenv("RAG_API_BASE_URL", "http://localhost:7001")
BACKEND_BASE_URL = "http://localhost:5001"
DB_PATH = "../llm_evaluation.db" # Relative to server directory

def get_folders_from_db():
    """Get folder paths from the SQLite database"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Check if the folders table exists
        cursor.execute("SELECT * FROM sqlite_master WHERE type='table' AND name='folders'")
        if not cursor.fetchone():
            print("Warning: 'folders' table does not exist in the database.")
            conn.close()
            return []

        # Get folder paths from the database
        cursor.execute("SELECT id, path FROM folders")
        folders = cursor.fetchall()

        if not folders:
            print("No folders found in the database.")
            conn.close()
            return []

        print(f"Found {len(folders)} folders in the database.")

        # Debug: Check documents and llm_responses tables
        try:
            cursor.execute("SELECT COUNT(*) FROM documents")
            doc_count = cursor.fetchone()[0]
            print(f"[DEBUG] Current document count in documents table: {doc_count}")

            cursor.execute("SELECT COUNT(*) FROM llm_responses")
            resp_count = cursor.fetchone()[0]
            print(f"[DEBUG] Current response count in llm_response table: {resp_count}")
        except sqlite3.Error as e:
            print(f"[DEBUG] Could not query document/response counts: {e}")

        conn.close()
        return folders
    except sqlite3.Error as e:
        print(f"SQLite error: {e}")
        return []
    except Exception as e:
        print(f"Error accessing database: {e}")
        return []


def _sanitize_path(path: str) -> str:
    """Remove surrounding quotes from path string if present."""
    return path.strip().strip("'\"")


def _validate_folder_path(folder_path: str) -> str:
    """Validate and normalize folder path, raising appropriate exceptions."""
    # First sanitize the path to remove any surrounding quotes
    sanitized_path = _sanitize_path(folder_path)
    normalized_path = os.path.abspath(sanitized_path)

    if not os.path.exists(normalized_path):
        raise FileNotFoundError(f"Folder {normalized_path} does not exist.")

    if not os.path.isdir(normalized_path):
        raise NotADirectoryError(f"{normalized_path} is not a directory.")

    return normalized_path


def get_files_from_folder(folder_path: str) -> List[str]:
    """Get supported document files from a folder.

    Args:
        folder_path: Path to the folder to scan

    Returns:
        List of absolute paths to supported document files
    """

    # Validate and normalize the folder path
    validated_path = _validate_folder_path(folder_path)

    # Define supported file extensions based on the document_processor_plan.md
    supported_extensions = [".pdf", ".txt", ".docx", ".xlsx"]

    # Use pathlib to recursively find all files with supported extensions
    files = []
    for ext in supported_extensions:
        # Recursively scan for files with the current extension
        for file_path in Path(validated_path).glob(f"**/*{ext}"):
            if file_path.is_file():
                files.append(str(file_path))

    print(f"Found {len(files)} supported files in folder {folder_path}")

    # Optionally print some file paths for debugging
    if files:
        sample_size = min(3, len(files))
        print(f"Sample of found files: {files[:sample_size]}")

    return files

def store_files_in_db(files: List[str]):
    """Store file paths in the documents table"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        # Insert files into documents table
        for file_path in files:
            try:
                filepath, filename = os.path.split(file_path)
                cursor.execute("INSERT OR IGNORE INTO documents (filepath, filename) VALUES (?, ?)",
                               (filepath, filename))

                conn.commit()
                print(f"Successfully stored {len(files)} files in documents table")
            except sqlite3.Error as e:
                print(f"SQLite error storing files: {e}")
    finally:
        conn.close()


def run_backend_test():
    print("--- Starting Backend Test ---")

    # 1. Fetch LLM configurations and prompts from the backend
    print("\nFetching LLM configurations...")
    try:
        llm_configs_response = requests.get(f"{BACKEND_BASE_URL}/llm-configs")
        llm_configs_response.raise_for_status()
        llm_configs = llm_configs_response.json().get('llmConfigs', [])
        print(f"Found {len(llm_configs)} LLM configurations.")
        if not llm_configs:
            print("No LLM configurations found. Please add some to the database.")
            return
        for config in llm_configs:
            print(f"  - {config.get('llm_name')}: {config.get('base_url')}")
    
    except requests.exceptions.RequestException as e:
        print(f"Error fetching LLM configurations: {e}")
        return  # Function exits, but calling code continues
    
    print("\nFetching prompts...")
    try:
        prompts_response = requests.get(f"{BACKEND_BASE_URL}/api/prompts")
        prompts_response.raise_for_status()
        prompts = prompts_response.json().get('prompts', [])
        print(f"Found {len(prompts)} prompts.")
        if not prompts:
            print("No prompts found. Please add some to the database.")
            return
        for prompt in prompts:
            print(f"  - {prompt.get('prompt_text')}")
    except requests.exceptions.RequestException as e:
        print(f"Error fetching prompts: {e}")
        return
    
    # 2. Get folders from database
    print("\nGetting folders from database...")
    folders = get_folders_from_db()

    if not folders:
        print("\nNo folders found in database. Please add folders to the database.")
        return

    # Verify that the folders in the database exist and contain supported files
    print("\nVerifying folders from database...")
    file_count = 0
    all_files = []
    for id, path in folders:
        print(f"\nScanning folder (ID: {id}): {path}")
        folder_files = get_files_from_folder(path)
        all_files.extend(folder_files)
        file_count += len(folder_files)

    # Store all found files in the documents table
    if all_files:
        store_files_in_db(all_files)

    if file_count == 0:
        print("\nNo supported files found in any of the database folders. Please add files to the folders.")
        return

    print(f"\nFound a total of {file_count} supported files across all folders in the database.")
    
    # 3. Call the process-db-folders endpoint to process all files in database folders
    print("\nProcessing all files from database folders...")
    try:
        # Try different variations of the endpoint path
        endpoint_paths = [
            "/process-db-folders", 
        ]

        process_response = None
        for path in endpoint_paths:
            full_url = f"{BACKEND_BASE_URL}{path}"
            print(f"Trying endpoint: {full_url}")
            try:
                process_response = requests.post(full_url)
                if process_response.status_code == 200:
                    print(f"✅ Successful with endpoint: {path}")
                    break
                else:
                    print(f"❌ Failed with status {process_response.status_code} at endpoint: {path}")
            except requests.exceptions.RequestException as e:
                print(f"❌ Error with endpoint {path}: {e}")

        if not process_response or process_response.status_code != 200:
            print("All endpoint variations failed.")
            if process_response:
                print(f"Using last attempt: {process_response.status_code}")
        print(f"Response status code: {process_response.status_code}")
        print(f"Response headers: {process_response.headers}")
        print(f"Response text: {process_response.text}")
        process_response.raise_for_status()
        process_data = process_response.json()
        print(f"Backend response for database folders: {process_data}")

        total_files_expected = process_data.get('totalFiles')
        message = process_data.get('message')

        if total_files_expected == 0:
            print("Backend reported no supported files to process. Test finished.")
            return

        print(f"Backend initiated processing: {message}")
        print(f"Expected total combinations to process: {total_files_expected}")

        # 4. Monitor progress and poll for status
        print("\nStarting to poll for status and progress...")
        poll_start_time = time.time()
        polling_interval = 5 # seconds
        timeout = 5 * 60 # 5 minutes

        processed_count = 0
        while processed_count < total_files_expected and (time.time() - poll_start_time < timeout):
            time.sleep(polling_interval)

            # Fetch progress
            progress_response = requests.get(f"{BACKEND_BASE_URL}/api/progress")
            progress_response.raise_for_status()
            progress_data = progress_response.json()

            current_processed = progress_data.get('processedDocuments', 0)
            current_outstanding = progress_data.get('outstandingDocuments', 0)

            print(f"Progress: Processed {current_processed}/{total_files_expected}, Outstanding: {current_outstanding}")

            if current_processed > processed_count:
                # Fetch errors if any new documents were processed
                errors_response = requests.get(f"{BACKEND_BASE_URL}/api/errors")
                errors_response.raise_for_status()
                errors_data = errors_response.json()
                if errors_data.get('errors'):
                    print("--- Current Errors ---")
                    for error in errors_data['errors']:
                        print(f"  File: {error.get('filename')}, LLM: {error.get('llm_name')}, Prompt: {error.get('prompt_text')}, Error: {error.get('error_message')}")
                    print("----------------------")

                processed_count = current_processed

            if current_processed == total_files_expected and total_files_expected > 0:
                print("\nAll expected documents processed. Test finished successfully.")
                break
        else:
            if processed_count < total_files_expected:
                print(f"\nTimeout: Not all documents processed within {timeout} seconds. Processed {processed_count}/{total_files_expected}.")
            else:
                print("\nAll expected documents processed. Test finished successfully.")

    except requests.exceptions.RequestException as e:
        print(f"Error processing database folders: {e}")
        if hasattr(e, 'response') and e.response:
            print(f"Response content: {e.response.text}")
        return
    except Exception as e:
        print(f"An unexpected error occurred: {e}")

    print("\n--- Backend Test Finished ---")


def check_db_stats():
    """Check database statistics after processing"""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()

        cursor.execute("SELECT COUNT(*) FROM documents")
        doc_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM llm_responses")
        resp_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE status = 'C'")
        completed_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE status = 'E'")
        error_count = cursor.fetchone()[0]

        cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE status = 'P'")
        processing_count = cursor.fetchone()[0]

        print("\n--- Database Statistics ---")
        print(f"Total documents: {doc_count}")
        print(f"Total LLM responses: {resp_count}")
        print(f"Completed responses: {completed_count}")
        print(f"Error responses: {error_count}")
        print(f"Processing responses: {processing_count}")

        conn.close()
    except sqlite3.Error as e:
        print(f"Error checking database stats: {e}")


if __name__ == "__main__":
    try:
        run_backend_test()
        # Check final database statistics
        check_db_stats()
    finally:
        # Ensure thread resources are properly cleaned up
        # This prevents the 'NoneType' object context manager error during shutdown
        import concurrent.futures
        import sys

        # Get all ThreadPoolExecutors from the concurrent.futures module
        for obj in list(sys._current_frames().values()):
            if isinstance(obj, concurrent.futures.ThreadPoolExecutor):
                print("Shutting down ThreadPoolExecutor...")
                obj.shutdown(wait=True)

        print("Cleanup complete.")