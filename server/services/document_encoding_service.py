"""
Document Encoding Service
Handles encoding, storing, and retrieving document content for the two-stage batch processing system.
"""

import os
import base64
import mimetypes
from typing import Optional, Dict, Any
from sqlalchemy.orm import Session
from server.models import Doc, Document

class DocumentEncodingService:
    """Service for encoding and storing document content"""

    def __init__(self):
        self.supported_extensions = {
            '.pdf', '.doc', '.docx', '.txt', '.rtf', '.odt',
            '.xls', '.xlsx', '.csv', '.ppt', '.pptx',
            '.jpg', '.jpeg', '.png', '.gif', '.bmp', '.tiff',
            '.html', '.htm', '.xml', '.json', '.md'
        }

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

            # Extract document type from file extension
            _, ext = os.path.splitext(file_path.lower())
            doc_type = ext[1:] if ext.startswith('.') else ext  # Remove the dot from extension

            # Read and encode file content
            with open(file_path, 'rb') as file:
                file_content = file.read()
                encoded_content = base64.b64encode(file_content)

            # Create doc record
            doc = Doc(
                content=encoded_content,
                content_type=content_type,
                doc_type=doc_type,
                file_size=file_size,
                encoding='base64'
            )

            session.add(doc)
            session.flush()  # Get the ID without committing

            print(f"✅ Encoded document: {file_path} (ID: {doc.id}, Size: {file_size} bytes)")
            return doc.id

        except Exception as e:
            print(f"❌ Failed to encode document {file_path}: {e}")
            return None

    def get_encoded_document(self, doc_id: int, session: Session) -> Optional[Dict[str, Any]]:
        """
        Retrieve encoded document content by doc_id.

        Args:
            doc_id: ID of the document in docs table
            session: Database session

        Returns:
            Dictionary with document data or None if not found
        """
        try:
            doc = session.query(Doc).filter(Doc.id == doc_id).first()
            if not doc:
                return None

            return {
                'id': doc.id,
                'content': doc.content.decode('utf-8') if doc.encoding == 'base64' else doc.content,
                'content_type': doc.content_type,
                'doc_type': doc.doc_type,
                'file_size': doc.file_size,
                'encoding': doc.encoding,
                'created_at': doc.created_at.isoformat() if doc.created_at else None
            }

        except Exception as e:
            print(f"❌ Failed to retrieve encoded document {doc_id}: {e}")
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
        try:
            if not document.doc_id:
                print(f"❌ Document {document.id} has no doc_id")
                return None

            # Get encoded content
            doc_data = self.get_encoded_document(document.doc_id, session)
            if not doc_data:
                print(f"❌ Could not retrieve encoded content for document {document.id}")
                return None

            # Prepare data for LLM service
            llm_data = {
                'document_id': document.id,
                'filename': document.filename,
                'content': doc_data['content'],
                'content_type': doc_data['content_type'],
                'doc_type': doc_data['doc_type'],
                'encoding': doc_data['encoding'],
                'file_size': doc_data['file_size'],
                'document_meta_data': document.meta_data
            }

            return llm_data

        except Exception as e:
            print(f"❌ Failed to prepare document {document.id} for LLM: {e}")
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
        results = {}

        print(f"🔄 Starting batch encoding of {len(file_paths)} documents...")

        for i, file_path in enumerate(file_paths, 1):
            print(f"📄 Encoding {i}/{len(file_paths)}: {os.path.basename(file_path)}")
            doc_id = self.encode_and_store_document(file_path, session)
            results[file_path] = doc_id

        successful = sum(1 for doc_id in results.values() if doc_id is not None)
        print(f"✅ Batch encoding complete: {successful}/{len(file_paths)} successful")

        return results
