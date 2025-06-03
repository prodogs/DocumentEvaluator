"""
Document Type Service - Manages valid document types and validation
"""

import os
from typing import List, Dict, Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import text
from database import Session as DatabaseSession
from contextlib import contextmanager
import mimetypes
import logging

logger = logging.getLogger(__name__)

@contextmanager
def get_db_session():
    """Context manager for database sessions"""
    session = DatabaseSession()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()

class DocumentTypeService:
    """Service for managing document types and validation"""
    
    def __init__(self):
        self._valid_extensions_cache = None
        self._mime_type_cache = None
    
    def get_valid_extensions(self) -> List[str]:
        """Get list of valid file extensions from database"""
        if self._valid_extensions_cache is None:
            self._refresh_cache()
        return self._valid_extensions_cache or []
    
    def get_mime_type_mapping(self) -> Dict[str, str]:
        """Get mapping of file extensions to MIME types"""
        if self._mime_type_cache is None:
            self._refresh_cache()
        return self._mime_type_cache or {}
    
    def _refresh_cache(self):
        """Refresh the cached valid extensions and MIME types from database"""
        try:
            with get_db_session() as session:
                # Query valid document types
                result = session.execute(text("""
                    SELECT file_extension, mime_type 
                    FROM document_types 
                    WHERE is_valid = true AND supports_text_extraction = true
                    ORDER BY file_extension
                """))
                
                extensions = []
                mime_types = {}
                
                for row in result:
                    ext = row.file_extension
                    extensions.append(ext)
                    if row.mime_type:
                        mime_types[ext] = row.mime_type
                
                self._valid_extensions_cache = extensions
                self._mime_type_cache = mime_types
                
                logger.info(f"Loaded {len(extensions)} valid document types from database")
                
        except Exception as e:
            logger.error(f"Failed to load document types from database: {e}")
            # Fallback to basic types if database is unavailable
            self._valid_extensions_cache = ['.txt', '.pdf', '.docx', '.doc']
            self._mime_type_cache = {
                '.txt': 'text/plain',
                '.pdf': 'application/pdf',
                '.docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
                '.doc': 'application/msword'
            }
    
    def is_valid_file_type(self, filename: str) -> bool:
        """Check if a file type is valid for processing"""
        if not filename:
            return False
            
        # Get file extension
        _, ext = os.path.splitext(filename.lower())
        
        # Check against valid extensions
        valid_extensions = self.get_valid_extensions()
        return ext in valid_extensions
    
    def get_file_type_info(self, filename: str) -> Dict[str, any]:
        """Get comprehensive information about a file type"""
        if not filename:
            return {
                'extension': None,
                'is_valid': False,
                'mime_type': None,
                'description': 'No filename provided'
            }
        
        _, ext = os.path.splitext(filename.lower())
        
        try:
            with get_db_session() as session:
                result = session.execute(text("""
                    SELECT file_extension, mime_type, description, is_valid, supports_text_extraction
                    FROM document_types 
                    WHERE file_extension = :ext
                """), {'ext': ext})
                
                row = result.fetchone()
                
                if row:
                    return {
                        'extension': row.file_extension,
                        'is_valid': row.is_valid and row.supports_text_extraction,
                        'mime_type': row.mime_type,
                        'description': row.description,
                        'supports_text_extraction': row.supports_text_extraction
                    }
                else:
                    # Unknown file type
                    return {
                        'extension': ext,
                        'is_valid': False,
                        'mime_type': mimetypes.guess_type(filename)[0],
                        'description': f'Unknown file type: {ext}',
                        'supports_text_extraction': False
                    }
                    
        except Exception as e:
            logger.error(f"Failed to get file type info for {filename}: {e}")
            return {
                'extension': ext,
                'is_valid': False,
                'mime_type': None,
                'description': f'Error checking file type: {e}',
                'supports_text_extraction': False
            }
    
    def validate_file_batch(self, filenames: List[str]) -> Tuple[List[str], List[str]]:
        """Validate a batch of files, returning valid and invalid lists"""
        valid_files = []
        invalid_files = []
        
        for filename in filenames:
            if self.is_valid_file_type(filename):
                valid_files.append(filename)
            else:
                invalid_files.append(filename)
        
        return valid_files, invalid_files
    
    def get_supported_extensions_list(self) -> str:
        """Get a human-readable list of supported extensions"""
        extensions = self.get_valid_extensions()
        if not extensions:
            return "No supported file types configured"
        
        # Group by category for better readability
        text_formats = [ext for ext in extensions if ext in ['.txt', '.md', '.rtf']]
        office_formats = [ext for ext in extensions if ext in ['.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx']]
        pdf_formats = [ext for ext in extensions if ext in ['.pdf']]
        code_formats = [ext for ext in extensions if ext in ['.py', '.js', '.java', '.cpp', '.c', '.h', '.cs', '.php', '.rb', '.go', '.rs']]
        data_formats = [ext for ext in extensions if ext in ['.json', '.yaml', '.yml', '.csv', '.xml', '.html']]
        other_formats = [ext for ext in extensions if ext not in text_formats + office_formats + pdf_formats + code_formats + data_formats]
        
        categories = []
        if text_formats:
            categories.append(f"Text: {', '.join(text_formats)}")
        if office_formats:
            categories.append(f"Office: {', '.join(office_formats)}")
        if pdf_formats:
            categories.append(f"PDF: {', '.join(pdf_formats)}")
        if code_formats:
            categories.append(f"Code: {', '.join(code_formats)}")
        if data_formats:
            categories.append(f"Data: {', '.join(data_formats)}")
        if other_formats:
            categories.append(f"Other: {', '.join(other_formats)}")
        
        return "; ".join(categories)
    
    def add_document_type(self, extension: str, mime_type: str = None, description: str = None, 
                         is_valid: bool = True, supports_text_extraction: bool = True) -> bool:
        """Add a new document type to the database"""
        try:
            # Ensure extension starts with a dot
            if not extension.startswith('.'):
                extension = '.' + extension
            
            extension = extension.lower()
            
            with get_db_session() as session:
                session.execute(text("""
                    INSERT INTO document_types (file_extension, mime_type, description, is_valid, supports_text_extraction)
                    VALUES (:ext, :mime, :desc, :valid, :supports)
                    ON CONFLICT (file_extension) DO UPDATE SET
                        mime_type = EXCLUDED.mime_type,
                        description = EXCLUDED.description,
                        is_valid = EXCLUDED.is_valid,
                        supports_text_extraction = EXCLUDED.supports_text_extraction,
                        updated_at = CURRENT_TIMESTAMP
                """), {
                    'ext': extension,
                    'mime': mime_type,
                    'desc': description or f"File type: {extension}",
                    'valid': is_valid,
                    'supports': supports_text_extraction
                })
                
                session.commit()
                
            # Clear cache to force refresh
            self._valid_extensions_cache = None
            self._mime_type_cache = None
            
            logger.info(f"Added/updated document type: {extension}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to add document type {extension}: {e}")
            return False
    
    def update_document_type_validity(self, extension: str, is_valid: bool) -> bool:
        """Update the validity of a document type"""
        try:
            if not extension.startswith('.'):
                extension = '.' + extension
            
            extension = extension.lower()
            
            with get_db_session() as session:
                result = session.execute(text("""
                    UPDATE document_types 
                    SET is_valid = :valid, updated_at = CURRENT_TIMESTAMP
                    WHERE file_extension = :ext
                """), {'valid': is_valid, 'ext': extension})
                
                session.commit()
                
                if result.rowcount > 0:
                    # Clear cache to force refresh
                    self._valid_extensions_cache = None
                    self._mime_type_cache = None
                    
                    logger.info(f"Updated document type {extension} validity to {is_valid}")
                    return True
                else:
                    logger.warning(f"Document type {extension} not found for update")
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to update document type {extension}: {e}")
            return False
    
    def get_all_document_types(self) -> List[Dict[str, any]]:
        """Get all document types from database for admin purposes"""
        try:
            with get_db_session() as session:
                result = session.execute(text("""
                    SELECT file_extension, mime_type, description, is_valid, 
                           supports_text_extraction, created_at, updated_at
                    FROM document_types 
                    ORDER BY is_valid DESC, file_extension
                """))
                
                return [dict(row._mapping) for row in result]
                
        except Exception as e:
            logger.error(f"Failed to get all document types: {e}")
            return []

# Global instance
document_type_service = DocumentTypeService()