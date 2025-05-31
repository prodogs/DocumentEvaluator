"""
Folder Preprocessing Service

Handles the new folder preprocessing workflow:
1. Select and Name Folder
2. Scan all files under folder
3. Create document records for ALL files
4. Mark files as valid='Y' or valid='N'
5. Store all files in docs table with file size
"""

import os
import logging
import mimetypes
from typing import List, Dict, Tuple, Optional
from pathlib import Path
import base64

from database import Session
from models import Folder, Document, Doc
from sqlalchemy import text, case

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class FolderPreprocessingService:
    """Service for preprocessing folders before batch creation"""

    # File validation criteria
    VALID_EXTENSIONS = {
        '.pdf', '.txt', '.docx', '.doc', '.xlsx', '.xls',
        '.pptx', '.ppt', '.rtf', '.odt', '.ods', '.odp',
        '.csv', '.tsv', '.json', '.xml', '.html', '.htm'
    }

    MAX_FILE_SIZE = 50 * 1024 * 1024  # 50MB limit
    MIN_FILE_SIZE = 1  # 1 byte minimum

    def __init__(self):
        self.session = None

    def preprocess_folder_async(self, folder_path: str, folder_name: str, task_id: str, app=None) -> Dict:
        """
        Preprocess a folder asynchronously with progress updates

        Args:
            folder_path: Path to the folder to preprocess
            folder_name: User-provided name for the folder
            task_id: Task ID for progress tracking
            app: Flask app instance for context (optional)

        Returns:
            Dict with processing results
        """
        try:
            # Update task status
            def update_task_status(**kwargs):
                if app and hasattr(app, 'preprocessing_tasks') and task_id in app.preprocessing_tasks:
                    app.preprocessing_tasks[task_id].update(kwargs)

            # 1. Connect to database
            self.session = Session()

            update_task_status(status='SCANNING')

            # 2. Update folder status to PREPROCESSING
            folder_id = self._get_or_create_folder(folder_path, folder_name)
            self._update_folder_status(folder_id, 'PREPROCESSING')
            self.session.commit()

            update_task_status(folder_id=folder_id, status='PROCESSING')

            logger.info(f"🔄 Starting preprocessing for folder: {folder_name} (ID: {folder_id})")

            # 3. Scan all files in folder
            files_info, directory_count = self._scan_folder_files(folder_path)
            logger.info(f"📁 Found {len(files_info)} files and {directory_count} directories in folder")

            update_task_status(total_files=len(files_info), status='PROCESSING_FILES')

            # 4. Process each file with progress updates
            results = {
                'folder_id': folder_id,
                'folder_name': folder_name,
                'total_files': len(files_info),
                'total_directories': directory_count,
                'valid_files': 0,
                'invalid_files': 0,
                'total_size': 0,
                'errors': []
            }

            for i, file_info in enumerate(files_info):
                try:
                    self._process_single_file(folder_id, file_info, results)
                    self.session.commit()  # Commit after each file

                    # Update progress
                    progress = int((i + 1) / len(files_info) * 90)  # 90% for file processing
                    update_task_status(
                        processed_files=i + 1,
                        valid_files=results['valid_files'],
                        invalid_files=results['invalid_files'],
                        progress=progress
                    )

                except Exception as e:
                    self.session.rollback()
                    error_msg = f"Error processing {file_info['path']}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)

            # 5. Update folder status to READY
            self._update_folder_status(folder_id, 'READY')
            self.session.commit()

            update_task_status(status='COMPLETED', progress=100)

            logger.info(f"✅ Preprocessing completed: {results['valid_files']} valid, {results['invalid_files']} invalid files")
            return results

        except Exception as e:
            logger.error(f"❌ Folder preprocessing failed: {e}")
            if self.session:
                self.session.rollback()
            raise e
        finally:
            if self.session:
                self.session.close()

    def preprocess_folder(self, folder_path: str, folder_name: str) -> Dict:
        """
        Preprocess a folder: scan files, validate, and store

        Args:
            folder_path: Path to the folder to preprocess
            folder_name: User-provided name for the folder

        Returns:
            Dict with preprocessing results
        """
        try:
            self.session = Session()

            # 1. Validate folder exists
            if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                raise ValueError(f"Folder does not exist: {folder_path}")

            # 2. Update folder status to PREPROCESSING
            folder_id = self._get_or_create_folder(folder_path, folder_name)
            self._update_folder_status(folder_id, 'PREPROCESSING')
            self.session.commit()

            logger.info(f"🔄 Starting preprocessing for folder: {folder_name} (ID: {folder_id})")

            # 3. Scan all files in folder
            files_info, directory_count = self._scan_folder_files(folder_path)
            logger.info(f"📁 Found {len(files_info)} files and {directory_count} directories in folder")

            # 4. Process each file
            results = {
                'folder_id': folder_id,
                'folder_name': folder_name,
                'total_files': len(files_info),
                'total_directories': directory_count,
                'valid_files': 0,
                'invalid_files': 0,
                'total_size': 0,
                'errors': []
            }

            for file_info in files_info:
                try:
                    self._process_single_file(folder_id, file_info, results)
                    self.session.commit()  # Commit after each file to avoid transaction issues
                except Exception as e:
                    self.session.rollback()  # Rollback on error
                    error_msg = f"Error processing {file_info['path']}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)

            # 5. Update folder status to READY
            self._update_folder_status(folder_id, 'READY')
            self.session.commit()

            logger.info(f"✅ Preprocessing completed: {results['valid_files']} valid, {results['invalid_files']} invalid files")
            return results

        except Exception as e:
            if self.session:
                self.session.rollback()
                # Update folder status to ERROR
                try:
                    if 'folder_id' in locals():
                        self._update_folder_status(folder_id, 'ERROR')
                        self.session.commit()
                except Exception:
                    pass
            logger.error(f"❌ Folder preprocessing failed: {e}")
            raise
        finally:
            if self.session:
                self.session.close()

    def _get_or_create_folder(self, folder_path: str, folder_name: str) -> int:
        """Get existing folder or create new one"""
        from models import Folder

        # Check if folder already exists
        existing_folder = self.session.query(Folder).filter(Folder.folder_path == folder_path).first()

        if existing_folder:
            # Update folder name if different
            existing_folder.folder_name = folder_name
            existing_folder.status = 'PREPROCESSING'
            self.session.flush()  # Get the ID without committing
            return existing_folder.id
        else:
            # Create new folder
            new_folder = Folder(
                folder_name=folder_name,
                folder_path=folder_path,
                active=1,
                status='PREPROCESSING'
            )
            self.session.add(new_folder)
            self.session.flush()  # Get the ID without committing
            return new_folder.id

    def _update_folder_status(self, folder_id: int, status: str):
        """Update folder preprocessing status"""
        from models import Folder

        folder = self.session.query(Folder).filter(Folder.id == folder_id).first()
        if folder:
            folder.status = status
            self.session.flush()

    def _scan_folder_files(self, folder_path: str) -> Tuple[List[Dict], int]:
        """Scan folder and return list of all files with metadata and directory count"""
        files_info = []
        directories = set()
        folder_path = Path(folder_path)

        for item_path in folder_path.rglob('*'):
            if item_path.is_file():
                try:
                    stat = item_path.stat()
                    files_info.append({
                        'path': str(item_path),
                        'relative_path': str(item_path.relative_to(folder_path)),
                        'name': item_path.name,
                        'size': stat.st_size,
                        'extension': item_path.suffix.lower(),
                        'mime_type': mimetypes.guess_type(str(item_path))[0] or 'application/octet-stream'
                    })
                except Exception as e:
                    logger.warning(f"Could not get info for file {item_path}: {e}")
            elif item_path.is_dir():
                # Count unique directories (excluding the root folder itself)
                try:
                    relative_dir = str(item_path.relative_to(folder_path))
                    if relative_dir != '.':  # Exclude the root folder
                        directories.add(relative_dir)
                except Exception as e:
                    logger.warning(f"Could not get relative path for directory {item_path}: {e}")

        return files_info, len(directories)

    def _validate_file(self, file_info: Dict) -> Tuple[bool, str]:
        """
        Validate if file should be processed

        Returns:
            Tuple of (is_valid, reason)
        """
        # Check file size
        if file_info['size'] < self.MIN_FILE_SIZE:
            return False, "File too small"

        if file_info['size'] > self.MAX_FILE_SIZE:
            return False, f"File too large (>{self.MAX_FILE_SIZE/1024/1024:.1f}MB)"

        # Check file extension
        if file_info['extension'] not in self.VALID_EXTENSIONS:
            return False, f"Unsupported file type: {file_info['extension']}"

        # Check if file is readable
        try:
            with open(file_info['path'], 'rb') as f:
                f.read(1)  # Try to read first byte
        except Exception as e:
            return False, f"File not readable: {str(e)}"

        return True, "Valid"

    def _process_single_file(self, folder_id: int, file_info: Dict, results: Dict):
        """Process a single file: validate, create document record, store in docs"""
        from models import Document, Doc

        # 1. Validate file
        is_valid, validation_reason = self._validate_file(file_info)
        valid_flag = 'Y' if is_valid else 'N'

        # 2. Prepare metadata with validation information
        meta_data = {
            'validation_reason': validation_reason,
            'file_size': file_info['size'],
            'file_extension': file_info['extension'],
            'relative_path': file_info['relative_path']
        }

        # 3. Create document record
        document = Document(
            folder_id=folder_id,
            filepath=file_info['path'],
            filename=file_info['name'],
            valid=valid_flag,
            meta_data=meta_data
        )
        self.session.add(document)
        self.session.flush()  # Get the ID without committing

        # 3. Read and encode file content
        try:
            with open(file_info['path'], 'rb') as f:
                file_content = f.read()

            encoded_content = base64.b64encode(file_content)

            # 4. Store in docs table with file size
            doc = Doc(
                document_id=document.id,
                doc_type=file_info['extension'][1:] if file_info['extension'] else 'unknown',
                content=encoded_content,
                file_size=file_info['size']
            )
            self.session.add(doc)

            # 5. Update results
            results['total_size'] += file_info['size']
            if is_valid:
                results['valid_files'] += 1
            else:
                results['invalid_files'] += 1
                logger.info(f"📄 Invalid file: {file_info['relative_path']} - {validation_reason}")

        except Exception as e:
            # If we can't read/encode the file, mark as invalid
            document.valid = 'N'
            self.session.flush()

            results['invalid_files'] += 1
            logger.error(f"❌ Failed to process file {file_info['path']}: {e}")

    def get_folder_status(self, folder_id: int) -> Optional[Dict]:
        """Get folder preprocessing status and statistics"""
        session = Session()
        try:
            from models import Folder, Document, Doc
            from sqlalchemy import func

            # Query folder with aggregated document statistics
            result = session.query(
                Folder.id,
                Folder.folder_name,
                Folder.folder_path,
                Folder.status,
                func.count(Document.id).label('total_documents'),
                func.sum(case((Document.valid == 'Y', 1), else_=0)).label('valid_documents'),
                func.sum(case((Document.valid == 'N', 1), else_=0)).label('invalid_documents'),
                func.coalesce(func.sum(Doc.file_size), 0).label('total_size'),
                func.coalesce(func.sum(case((Document.valid == 'Y', Doc.file_size), else_=0)), 0).label('ready_files_size')
            ).outerjoin(Document, Folder.id == Document.folder_id)\
             .outerjoin(Doc, Document.id == Doc.document_id)\
             .filter(Folder.id == folder_id)\
             .group_by(Folder.id, Folder.folder_name, Folder.folder_path, Folder.status)\
             .first()

            if result:
                # Get directory count by scanning the folder if it exists
                directory_count = 0
                folder_path = result[2]  # folder_path
                if folder_path and os.path.exists(folder_path):
                    try:
                        _, directory_count = self._scan_folder_files(folder_path)
                    except Exception as e:
                        logger.warning(f"Could not scan directory count for folder {folder_path}: {e}")

                return {
                    'folder_id': result[0],
                    'folder_name': result[1],
                    'folder_path': result[2],
                    'status': result[3],
                    'total_files': result[4],
                    'valid_files': result[5],
                    'invalid_files': result[6],
                    'total_size': result[7],
                    'ready_files_size': result[8],
                    'total_directories': directory_count,
                    'processed_files': result[4]  # For compatibility during processing
                }
            return None

        except Exception as e:
            logger.error(f"Error getting folder status: {e}")
            return None
        finally:
            session.close()
