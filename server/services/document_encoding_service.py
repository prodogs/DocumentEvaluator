"""
Document Encoding Service
Handles encoding, storing, and retrieving document content for the two-stage batch processing system.
"""

import os
import base64
import mimetypes
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from models import Document
from services.config import config_manager

class DocumentEncodingService:
    """Service for encoding and storing document content"""

    def __init__(self):
        self.supported_extensions = {
            '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt',
            '.xls', '.xlsx', '.csv', '.ppt', '.pptx',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
            '.html', '.htm', '.xml', '.json', '.md'
        }
        self.doc_config = config_manager.get_document_config()

    def encode_and_store_document(self, file_path: str, session: Session) -> Optional[int]:
        """
        Encode a document file and store it in the docs table.

        Args:
            file_path: Path to the document file
            session: Database session

        Returns:
            doc_id if successful, None if failed
        """
        try:
            # Validate file exists
            if not os.path.exists(file_path):
                print(f"❌ File not found: {file_path}")
                return None

            # Check file extension
            _, ext = os.path.splitext(file_path.lower())
            if ext not in self.supported_extensions:
                print(f"⚠️ Unsupported file type: {ext} for {file_path}")
                # Continue anyway - let the LLM service decide if it can handle it

            # Get file info
            file_size = os.path.getsize(file_path)
            content_type = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'

            # Validate file size
            if file_size > self.doc_config.max_file_size_bytes:
                print(f"❌ File too large: {file_path} ({file_size} bytes > {self.doc_config.max_file_size_display})")
                return None

            if file_size < self.doc_config.min_file_size_bytes:
                print(f"❌ File too small: {file_path} ({file_size} bytes)")
                return None

            # Extract document type from file extension
            _, ext = os.path.splitext(file_path.lower())
            doc_type = ext[1:] if ext.startswith('.') else ext  # Remove the dot from extension

            # Read and encode file content
            with open(file_path, 'rb') as file:
                file_content = file.read()
                encoded_content = base64.b64encode(file_content)

            # Note: docs table moved to KnowledgeDocuments database
            # Skip creating doc record since docs table is in separate database
            print(f"⚠️ Document encoding skipped: {file_path} (docs table moved to KnowledgeDocuments database)")
            return None

        except Exception as e:
            print(f"❌ Failed to encode document {file_path}: {e}")
            return None

    def get_encoded_document_by_path(self, file_path: str, session: Session) -> Optional[Dict[str, Any]]:
        """
        Retrieve encoded document content by file_path.

        Args:
            file_path: Path of the file in docs table
            session: Database session

        Returns:
            Dictionary with document data or None if not found
        """
        # Note: docs table moved to KnowledgeDocuments database
        print(f"⚠️ get_encoded_document_by_path called for {file_path} but docs table moved to KnowledgeDocuments database")
        return None

    def prepare_document_for_llm(self, document: Document, session: Session) -> Optional[Dict[str, Any]]:
        """
        Prepare document data for sending to LLM service.

        Args:
            document: Document model instance
            session: Database session

        Returns:
            Dictionary ready for LLM service or None if failed
        """
        # Note: docs table moved to KnowledgeDocuments database
        print(f"⚠️ prepare_document_for_llm called for document {document.id} but docs table moved to KnowledgeDocuments database")
        return None

    def batch_encode_documents(self, file_paths: list, session: Session) -> Dict[str, Optional[int]]:
        """
        Encode multiple documents in batch.

        Args:
            file_paths: List of file paths to encode
            session: Database session

        Returns:
            Dictionary mapping file_path -> doc_id (or None if failed)
        """
        # Note: docs table moved to KnowledgeDocuments database
        print(f"⚠️ batch_encode_documents called for {len(file_paths)} files but docs table moved to KnowledgeDocuments database")
        return {file_path: None for file_path in file_paths}
