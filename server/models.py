from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, LargeBinary
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from server.database import Base

class Batch(Base):
    __tablename__ = 'batches'
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_number = Column(Integer, unique=True, nullable=False)
    batch_name = Column(Text, nullable=True)  # User-friendly name
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())  # When batch was created
    started_at = Column(DateTime, nullable=True)  # When processing actually started
    completed_at = Column(DateTime, nullable=True)  # When processing completed
    status = Column(Text, default='PREPARED', nullable=False)  # PREPARED: Ready to run, PROCESSING: Running, COMPLETED: Finished, FAILED: Error
    total_documents = Column(Integer, default=0)
    processed_documents = Column(Integer, default=0)
    folder_path = Column(Text, nullable=True)  # Legacy: Path that was processed (deprecated)
    folder_ids = Column(JSON, nullable=True)  # Deprecated: JSON array of folder IDs (replaced by config_snapshot)
    meta_data = Column(JSON, nullable=True)  # JSON metadata to be sent to LLM for context
    config_snapshot = Column(JSON, nullable=True)  # Complete configuration snapshot at batch creation time

    documents = relationship("Document", back_populates="batch")

class Folder(Base):
    __tablename__ = 'folders'
    id = Column(Integer, primary_key=True, autoincrement=True)
    folder_path = Column(Text, unique=True, nullable=False)
    folder_name = Column(Text)
    active = Column(Integer, default=1, nullable=False)  # 0 = inactive, 1 = active
    created_at = Column(DateTime, default=func.now())

    documents = relationship("Document", back_populates="folder")

class Doc(Base):
    """Table to store encoded document content"""
    __tablename__ = 'docs'
    id = Column(Integer, primary_key=True, autoincrement=True)
    content = Column(LargeBinary, nullable=False)  # Base64 encoded document content
    content_type = Column(Text, nullable=True)  # MIME type of the document
    doc_type = Column(Text, nullable=True)  # Document type/extension (e.g., 'pdf', 'docx', 'txt')
    file_size = Column(Integer, nullable=True)  # Original file size in bytes
    encoding = Column(Text, default='base64', nullable=False)  # Encoding method used
    created_at = Column(DateTime, default=func.now())

    # Relationship to documents
    documents = relationship("Document", back_populates="doc")

class Document(Base):
    __tablename__ = 'documents'
    id = Column(Integer, primary_key=True, autoincrement=True)
    filepath = Column(Text, unique=True, nullable=False)
    filename = Column(Text, nullable=False)
    folder_id = Column(Integer, ForeignKey('folders.id'), nullable=True)
    batch_id = Column(Integer, ForeignKey('batches.id'), nullable=True)  # Link to batch
    doc_id = Column(Integer, ForeignKey('docs.id'), nullable=True)  # Link to encoded document content
    meta_data = Column(JSON, default={'meta_data': 'NONE'}, nullable=False)  # Document-level metadata
    created_at = Column(DateTime, default=func.now())
    task_id = Column(Text, nullable=True)  # Task ID for LLM processing recovery

    llm_responses = relationship("LlmResponse", back_populates="document")
    folder = relationship("Folder", back_populates="documents")
    batch = relationship("Batch", back_populates="documents")
    doc = relationship("Doc", back_populates="documents")

class Prompt(Base):
    __tablename__ = 'prompts'
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_text = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    active = Column(Integer, default=1, nullable=False)  # 0 = inactive, 1 = active

    llm_responses = relationship("LlmResponse", back_populates="prompt")

class LlmConfiguration(Base):
    __tablename__ = 'llm_configurations'
    id = Column(Integer, primary_key=True, autoincrement=True)
    llm_name = Column(Text, unique=True, nullable=False)
    base_url = Column(Text)
    model_name = Column(Text, nullable=False)
    api_key = Column(Text)
    provider_type = Column(Text)
    port_no = Column(Integer)
    active = Column(Integer, default=1, nullable=False)  # 0 = inactive, 1 = active

    llm_responses = relationship("LlmResponse", foreign_keys="LlmResponse.llm_config_id", back_populates="llm_config")

class LlmResponse(Base):
    __tablename__ = 'llm_responses'
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False)
    prompt_id = Column(Integer, ForeignKey('prompts.id'), nullable=False)
    llm_config_id = Column(Integer, ForeignKey('llm_configurations.id'), nullable=True)  # New: Full LLM configuration reference
    llm_name = Column(Text, ForeignKey('llm_configurations.llm_name'), nullable=False)  # Keep for backward compatibility
    task_id = Column(Text)
    status = Column(Text, default='R', nullable=False)  # R: Ready, P: Processing, S: Success, F: Failure
    started_processing_at = Column(DateTime)
    completed_processing_at = Column(DateTime)
    response_json = Column(Text)
    response_text = Column(Text)  # Added column for response text
    response_time_ms = Column(Integer)
    error_message = Column(Text)
    timestamp = Column(DateTime, default=func.now())

    document = relationship("Document", back_populates="llm_responses")
    prompt = relationship("Prompt", back_populates="llm_responses")
    llm_config = relationship("LlmConfiguration", foreign_keys=[llm_config_id], back_populates="llm_responses")

class BatchArchive(Base):
    __tablename__ = 'batch_archive'
    id = Column(Integer, primary_key=True, autoincrement=True)
    original_batch_id = Column(Integer, nullable=False)  # Original batch ID before deletion
    batch_number = Column(Integer, nullable=False)  # Original batch number
    batch_name = Column(Text, nullable=True)  # Original batch name
    archived_at = Column(DateTime, default=func.now())  # When the batch was archived
    archived_by = Column(Text, nullable=True)  # Who archived it (for future user tracking)
    archive_reason = Column(Text, default='Manual deletion')  # Why it was archived
    batch_data = Column(JSON, nullable=False)  # Complete batch data in JSON format
    documents_data = Column(JSON, nullable=False)  # All documents data in JSON format
    llm_responses_data = Column(JSON, nullable=False)  # All LLM responses data in JSON format
    archive_metadata = Column(JSON, nullable=True)  # Additional metadata (counts, stats, etc.)
