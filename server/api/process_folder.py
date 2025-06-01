import os
from models import Document, Connection, Prompt, LlmResponse
from database import Session
from services.batch_service import batch_service
import logging

logger = logging.getLogger(__name__)

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
        supported_extensions = {'.pdf', '.txt', '.docx', '.xlsx', '.doc', '.xls', '.rtf', '.odt', '.ods'}
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
        logger.error(f"Permission denied accessing directory: {path}", exc_info=True)
        raise PermissionError(f"Permission denied accessing directory: {path}") from e
    except Exception as e:
        logger.error(f"Error traversing directory {path}: {str(e)}", exc_info=True)
        raise

    return files

def process_folder(folder_path, task_id=None, batch_name=None, folder_id=None, batch_id=None):
    """Process all files in a folder

    Args:
        folder_path (str): Path to the folder to process
        task_id (str, optional): Task ID for tracking progress
        batch_name (str, optional): User-friendly name for the batch
        folder_id (int, optional): ID of the folder in the database
        batch_id (int, optional): ID of an existing batch to use (if provided, no new batch will be created)

    Returns:
        dict: Result of processing with totalFiles and processedFiles counts
    """
    try:
        logger.info(f"Starting process_folder for: {folder_path}, Task ID: {task_id}, Batch Name: {batch_name}, Batch ID: {batch_id}")

        # Import batch_service at the top to avoid scoping issues
        from services.batch_service import batch_service

        # Use existing batch or create a new one
        if batch_id is not None:
            # Use the provided batch_id (multi-folder batch scenario)
            logger.info(f"Using existing batch ID: {batch_id}")
            batch_name_final = batch_name or f"Multi-folder batch {batch_id}"
            batch_number = None  # Will be retrieved if needed
        else:
            # Create a new batch for this processing run (legacy single-folder scenario)
            batch_data = batch_service.create_batch(
                folder_path=folder_path,
                batch_name=batch_name,
                description=f"Processing folder: {folder_path}"
            )
            # Extract batch info from returned data
            batch_id = batch_data['id']
            batch_number = batch_data['batch_number']
            batch_name_final = batch_data['batch_name']
            logger.info(f"Created new batch #{batch_number} for processing")

        # Get all supported files in the folder
        files = traverse_directory(folder_path)

        if not files:
            logger.info(f"No supported files found in folder: {folder_path}")
            return {
                'totalFiles': 0,
                'processedFiles': 0,
                'message': f'No supported files found in folder: {folder_path}'
            }

        # Get only active connections and prompts
        session = Session()
        llm_configs = session.query(Connection).filter(Connection.is_active == True).all()
        prompts = session.query(Prompt).filter(Prompt.active == 1).all()

        if not llm_configs:
            session.close()
            logger.warning("No active connections found.")
            return {
                'totalFiles': len(files),
                'processedFiles': 0,
                'message': 'No active connections found'
            }

        if not prompts:
            session.close()
            logger.warning("No active prompts found.")
            return {
                'totalFiles': len(files),
                'processedFiles': 0,
                'message': 'No active prompts found'
            }

        # Check outstanding document limit (max 30 concurrent processing tasks)
        MAX_OUTSTANDING_DOCUMENTS = 30
        outstanding_count = session.query(LlmResponse).filter(LlmResponse.status == 'P').count()

        if outstanding_count >= MAX_OUTSTANDING_DOCUMENTS:
            session.close()
            logger.warning(f"Outstanding document limit reached: {outstanding_count}/{MAX_OUTSTANDING_DOCUMENTS} documents currently processing")
            return {
                'totalFiles': len(files) * len(llm_configs) * len(prompts),
                'processedFiles': 0,
                'message': f'Outstanding document limit reached: {outstanding_count}/{MAX_OUTSTANDING_DOCUMENTS} documents currently processing. Please wait for some tasks to complete.',
                'outstanding_count': outstanding_count,
                'max_outstanding': MAX_OUTSTANDING_DOCUMENTS
            }

        # Calculate available processing slots
        available_slots = MAX_OUTSTANDING_DOCUMENTS - outstanding_count
        logger.info(f"Outstanding documents: {outstanding_count}/{MAX_OUTSTANDING_DOCUMENTS}, Available slots: {available_slots}")

        # PHASE 1A: Create ALL documents first (batch operation)
        logger.info("Phase 1A: Creating all document records...")

        document_map = {}  # Map file_path to doc_id
        new_documents = []
        updated_documents = []

        for file_path in files:
            filename = os.path.basename(file_path)

            # Check if document already exists
            existing_doc = session.query(Document).filter_by(filepath=file_path).first()

            if not existing_doc:
                # Create new document record
                document = Document(
                    filepath=file_path,
                    filename=filename,
                    batch_id=batch_id,
                    folder_id=folder_id
                )
                session.add(document)
                new_documents.append(document)
                logger.debug(f"Prepared new document: {filename}")
            else:
                # Update existing document
                existing_doc.batch_id = batch_id
                if folder_id:
                    existing_doc.folder_id = folder_id
                updated_documents.append(existing_doc)
                document_map[file_path] = existing_doc.id
                logger.debug(f"Prepared existing document update: {filename}")

        # Commit all document changes at once
        session.commit()

        # Map file paths to document IDs for new documents
        for file_path in files:
            if file_path not in document_map:  # Only for new documents
                filename = os.path.basename(file_path)
                # Find the document we just created
                for document in new_documents:
                    if document.filename == filename and document.filepath == file_path:
                        document_map[file_path] = document.id
                        break

        logger.info(f"Phase 1A complete: Created {len(new_documents)} new documents, updated {len(updated_documents)} existing documents")

        # PHASE 1B: Create ALL LLM response records (batch operation)
        logger.info("Phase 1B: Creating all LLM response records...")

        all_combinations = []
        new_responses = []
        updated_responses = []

        # Generate all combinations upfront
        for file_path in files:
            filename = os.path.basename(file_path)
            doc_id = document_map[file_path]

            for llm_config in llm_configs:
                for prompt in prompts:
                    # Check if combination already exists
                    existing_response = session.query(LlmResponse).filter_by(
                        document_id=doc_id,
                        prompt_id=prompt.id,
                        llm_name=llm_config.llm_name
                    ).first()

                    if not existing_response:
                        # Create new LLM response record
                        llm_response = LlmResponse(
                            document_id=doc_id,
                            prompt_id=prompt.id,
                            llm_config_id=llm_config.id,
                            llm_name=llm_config.llm_name,
                            task_id=None,
                            status='N',  # Not started
                            started_processing_at=None
                        )
                        session.add(llm_response)
                        new_responses.append(llm_response)

                        # Track for processing
                        all_combinations.append({
                            'doc_id': doc_id,
                            'file_path': file_path,
                            'filename': filename,
                            'llm_config': llm_config,
                            'prompt': prompt,
                            'llm_response': llm_response
                        })
                        logger.debug(f"Prepared new LLM response: Doc {doc_id}, Prompt {prompt.id}, LLM {llm_config.llm_name}")
                    else:
                        # Reset existing record
                        existing_response.status = 'N'
                        existing_response.started_processing_at = None
                        existing_response.completed_processing_at = None
                        existing_response.task_id = None
                        existing_response.llm_config_id = llm_config.id
                        existing_response.llm_name = llm_config.llm_name
                        existing_response.error_message = None
                        existing_response.response_text = None
                        existing_response.response_time_ms = None
                        updated_responses.append(existing_response)

                        # Track for processing
                        all_combinations.append({
                            'doc_id': doc_id,
                            'file_path': file_path,
                            'filename': filename,
                            'llm_config': llm_config,
                            'prompt': prompt,
                            'llm_response': existing_response
                        })
                        logger.debug(f"Prepared existing LLM response reset: Doc {doc_id}, Prompt {prompt.id}, LLM {llm_config.llm_name}")

        # Commit all LLM response changes at once
        session.commit()

        logger.info(f"Phase 1B complete: Created {len(new_responses)} new LLM responses, updated {len(updated_responses)} existing responses")
        logger.info(f"Phase 1 TOTAL: {len(all_combinations)} document-LLM-prompt combinations ready for processing")

        # PHASE 2: Skip synchronous processing - let dynamic queue handle it
        logger.info("Phase 2: Skipping synchronous processing - dynamic queue will handle LLM responses asynchronously")

        # All LLM responses are created with status 'N' (not started)
        # The dynamic processing queue will automatically pick them up and process them
        processed_count = len(all_combinations)
        skipped_due_to_limit = 0

        logger.info(f"Created {processed_count} LLM response records ready for dynamic queue processing")

        session.close()
        total_combinations = len(files) * len(llm_configs) * len(prompts)

        # Create detailed completion message
        message_parts = [f'Processed {processed_count} file-LLM-prompt combinations']
        if skipped_due_to_limit > 0:
            message_parts.append(f'{skipped_due_to_limit} combinations skipped due to outstanding document limit ({MAX_OUTSTANDING_DOCUMENTS})')

        logger.info(f"Finished process_folder for: {folder_path}. Processed {processed_count}/{total_combinations} combinations, Skipped: {skipped_due_to_limit}")

        # Update batch progress
        batch_service.update_batch_progress(batch_id)

        return {
            'totalFiles': total_combinations,
            'processedFiles': processed_count,
            'skippedFiles': skipped_due_to_limit,
            'outstanding_limit': MAX_OUTSTANDING_DOCUMENTS,
            'batch_id': batch_id,
            'batch_number': batch_number,  # May be None for multi-folder batches
            'batch_name': batch_name_final,
            'message': '. '.join(message_parts)
        }

    except Exception as e:
        logger.error(f"Error in process_folder for {folder_path}: {e}", exc_info=True)
        if 'session' in locals():
            session.close()

        return {
            'totalFiles': 0,
            'processedFiles': 0,
            'error': str(e)
        }
