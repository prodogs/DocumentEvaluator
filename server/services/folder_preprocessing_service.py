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

from database import get_db_connection

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
        self.conn = None

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
            self.conn = get_db_connection()
            cursor = self.conn.cursor()

            # 1. Validate folder exists
            if not os.path.exists(folder_path) or not os.path.isdir(folder_path):
                raise ValueError(f"Folder does not exist: {folder_path}")

            # 2. Update folder status to PREPROCESSING
            folder_id = self._get_or_create_folder(cursor, folder_path, folder_name)
            self._update_folder_status(cursor, folder_id, 'PREPROCESSING')
            self.conn.commit()

            logger.info(f"🔄 Starting preprocessing for folder: {folder_name} (ID: {folder_id})")

            # 3. Scan all files in folder
            files_info = self._scan_folder_files(folder_path)
            logger.info(f"📁 Found {len(files_info)} files in folder")

            # 4. Process each file
            results = {
                'folder_id': folder_id,
                'folder_name': folder_name,
                'total_files': len(files_info),
                'valid_files': 0,
                'invalid_files': 0,
                'total_size': 0,
                'errors': []
            }

            for file_info in files_info:
                try:
                    self._process_single_file(cursor, folder_id, file_info, results)
                    self.conn.commit()  # Commit after each file to avoid transaction issues
                except Exception as e:
                    self.conn.rollback()  # Rollback on error
                    error_msg = f"Error processing {file_info['path']}: {str(e)}"
                    logger.error(error_msg)
                    results['errors'].append(error_msg)

            # 5. Update folder status to READY
            self._update_folder_status(cursor, folder_id, 'READY')
            self.conn.commit()

            logger.info(f"✅ Preprocessing completed: {results['valid_files']} valid, {results['invalid_files']} invalid files")
            return results

        except Exception as e:
            if self.conn:
                self.conn.rollback()
                # Update folder status to ERROR
                try:
                    cursor = self.conn.cursor()
                    if 'folder_id' in locals():
                        self._update_folder_status(cursor, folder_id, 'ERROR')
                        self.conn.commit()
                except:
                    pass
            logger.error(f"❌ Folder preprocessing failed: {e}")
            raise
        finally:
            if self.conn:
                self.conn.close()

    def _get_or_create_folder(self, cursor, folder_path: str, folder_name: str) -> int:
        """Get existing folder or create new one"""
        # Check if folder already exists
        cursor.execute("""
            SELECT id FROM folders
            WHERE folder_path = %s
        """, (folder_path,))

        result = cursor.fetchone()
        if result:
            folder_id = result[0]
            # Update folder name if different
            cursor.execute("""
                UPDATE folders
                SET folder_name = %s, status = 'PREPROCESSING'
                WHERE id = %s
            """, (folder_name, folder_id))
            return folder_id
        else:
            # Create new folder
            cursor.execute("""
                INSERT INTO folders (folder_name, folder_path, active, status)
                VALUES (%s, %s, 1, 'PREPROCESSING')
                RETURNING id
            """, (folder_name, folder_path))
            return cursor.fetchone()[0]

    def _update_folder_status(self, cursor, folder_id: int, status: str):
        """Update folder preprocessing status"""
        cursor.execute("""
            UPDATE folders
            SET status = %s
            WHERE id = %s
        """, (status, folder_id))

    def _scan_folder_files(self, folder_path: str) -> List[Dict]:
        """Scan folder and return list of all files with metadata"""
        files_info = []
        folder_path = Path(folder_path)

        for file_path in folder_path.rglob('*'):
            if file_path.is_file():
                try:
                    stat = file_path.stat()
                    files_info.append({
                        'path': str(file_path),
                        'relative_path': str(file_path.relative_to(folder_path)),
                        'name': file_path.name,
                        'size': stat.st_size,
                        'extension': file_path.suffix.lower(),
                        'mime_type': mimetypes.guess_type(str(file_path))[0] or 'application/octet-stream'
                    })
                except Exception as e:
                    logger.warning(f"Could not get info for file {file_path}: {e}")

        return files_info

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

    def _process_single_file(self, cursor, folder_id: int, file_info: Dict, results: Dict):
        """Process a single file: validate, create document record, store in docs"""

        # 1. Validate file
        is_valid, validation_reason = self._validate_file(file_info)
        valid_flag = 'Y' if is_valid else 'N'

        # 2. Create document record
        cursor.execute("""
            INSERT INTO documents (folder_id, filepath, filename, valid)
            VALUES (%s, %s, %s, %s)
            RETURNING id
        """, (folder_id, file_info['path'], file_info['name'], valid_flag))

        document_id = cursor.fetchone()[0]

        # 3. Read and encode file content
        try:
            with open(file_info['path'], 'rb') as f:
                file_content = f.read()

            encoded_content = base64.b64encode(file_content).decode('utf-8')

            # 4. Store in docs table with file size
            cursor.execute("""
                INSERT INTO docs (document_id, doc_type, content, file_size)
                VALUES (%s, %s, %s, %s)
            """, (document_id, file_info['extension'][1:] if file_info['extension'] else 'unknown',
                  encoded_content.encode('utf-8'), file_info['size']))

            # 5. Update results
            results['total_size'] += file_info['size']
            if is_valid:
                results['valid_files'] += 1
            else:
                results['invalid_files'] += 1
                logger.info(f"📄 Invalid file: {file_info['relative_path']} - {validation_reason}")

        except Exception as e:
            # If we can't read/encode the file, mark as invalid
            cursor.execute("""
                UPDATE documents
                SET valid = 'N'
                WHERE id = %s
            """, (document_id,))

            results['invalid_files'] += 1
            logger.error(f"❌ Failed to process file {file_info['path']}: {e}")

    def get_folder_status(self, folder_id: int) -> Optional[Dict]:
        """Get folder preprocessing status and statistics"""
        try:
            conn = get_db_connection()
            cursor = conn.cursor()

            cursor.execute("""
                SELECT f.id, f.folder_name, f.folder_path, f.status,
                       COUNT(d.id) as total_documents,
                       COUNT(CASE WHEN d.valid = 'Y' THEN 1 END) as valid_documents,
                       COUNT(CASE WHEN d.valid = 'N' THEN 1 END) as invalid_documents,
                       COALESCE(SUM(docs.file_size), 0) as total_size
                FROM folders f
                LEFT JOIN documents d ON f.id = d.folder_id
                LEFT JOIN docs ON d.id = docs.document_id
                WHERE f.id = %s
                GROUP BY f.id, f.folder_name, f.folder_path, f.status
            """, (folder_id,))

            result = cursor.fetchone()
            if result:
                return {
                    'folder_id': result[0],
                    'folder_name': result[1],
                    'folder_path': result[2],
                    'status': result[3],
                    'total_documents': result[4],
                    'valid_documents': result[5],
                    'invalid_documents': result[6],
                    'total_size': result[7]
                }
            return None

        except Exception as e:
            logger.error(f"Error getting folder status: {e}")
            return None
        finally:
            if conn:
                conn.close()
