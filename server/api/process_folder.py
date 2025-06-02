import os
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
        logger.error(f"Permission denied accessing directory: {path}", exc_info=True)
        raise PermissionError(f"Permission denied accessing directory: {path}") from e
    except Exception as e:
        logger.error(f"Error traversing directory {path}: {str(e)}", exc_info=True)
        raise

    return files

def process_folder(folder_path, task_id=None, batch_name=None, folder_id=None, batch_id=None):
    """DEPRECATED: Process folder functionality moved to KnowledgeDocuments database"""
    logger.warning(f"process_folder called for {folder_path} but service has been moved to KnowledgeDocuments database")

    return {
        'totalFiles': 0,
        'processedFiles': 0,
        'deprecated': True,
        'message': 'Process folder functionality has been moved to KnowledgeDocuments database',
        'reason': 'docs and llm_responses tables moved to separate database'
    }
