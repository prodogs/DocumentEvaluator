from sqlalchemy import Column, Integer, Text, DateTime, ForeignKey, JSON, LargeBinary, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from sqlalchemy.dialects.postgresql import JSONB
from database import Base

# Ensure we're using the correct Base class and avoid naming conflicts
__all__ = [
    'Batch', 'Folder', 'Doc', 'Document', 'Prompt',
    'BatchArchive', 'LlmProvider', 'Model', 'ProviderModel',
    'ModelAlias', 'LlmModel', 'Connection', 'Snapshot'
]

class Batch(Base):
    __tablename__ = 'batches'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    batch_number = Column(Integer, unique=True, nullable=False)
    batch_name = Column(Text, nullable=True)  # User-friendly name
    description = Column(Text, nullable=True)
    created_at = Column(DateTime, default=func.now())  # When batch was created
    started_at = Column(DateTime, nullable=True)  # When processing actually started
    completed_at = Column(DateTime, nullable=True)  # When processing completed
    status = Column(Text, default='P', nullable=False)  # P = Pending, SAVED, READY_FOR_STAGING, STAGING, STAGED, FAILED_STAGING, ANALYZING, COMPLETED
    total_documents = Column(Integer, default=0)
    processed_documents = Column(Integer, default=0)
    folder_path = Column(Text, nullable=True)  # Legacy: Path that was processed (deprecated)
    folder_ids = Column(JSONB, nullable=True)  # Deprecated: JSON array of folder IDs (replaced by config_snapshot)
    meta_data = Column(JSON, nullable=True)  # JSON metadata to be sent to LLM for context
    config_snapshot = Column(JSON, nullable=True)  # Complete configuration snapshot at batch creation time

    documents = relationship("Document", back_populates="batch")

class Folder(Base):
    __tablename__ = 'folders'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    folder_path = Column(Text, unique=True, nullable=False)
    folder_name = Column(Text)
    active = Column(Integer, default=1, nullable=True)  # Fixed: DB allows null
    status = Column(Text, default='NOT_PROCESSED', nullable=False)  # NOT_PROCESSED, PREPROCESSING, READY, ERROR
    created_at = Column(DateTime, default=func.now())

    documents = relationship("Document", back_populates="folder")

class Doc(Base):
    """Table to store encoded document content - completely independent storage layer"""
    __tablename__ = 'docs'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    file_path = Column(Text, unique=True, nullable=False)  # Natural key for linking
    content = Column(LargeBinary, nullable=False)  # Base64 encoded document content
    content_type = Column(Text, nullable=True)  # MIME type of the document
    doc_type = Column(Text, nullable=True)  # Document type/extension (e.g., 'pdf', 'docx', 'txt')
    file_size = Column(Integer, nullable=True)  # Original file size in bytes
    encoding = Column(Text, default='base64', nullable=False)  # Encoding method used
    created_at = Column(DateTime, default=func.now())

class Document(Base):
    __tablename__ = 'documents'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    filepath = Column(Text, unique=True, nullable=False)
    filename = Column(Text, nullable=False)
    folder_id = Column(Integer, ForeignKey('folders.id'), nullable=True)
    batch_id = Column(Integer, ForeignKey('batches.id'), nullable=True)  # Link to batch
    meta_data = Column(JSONB, default={}, nullable=True)  # Fixed: DB allows null, use JSONB for PostgreSQL
    valid = Column(Text, default='Y', nullable=False)  # Y = valid, N = invalid (for folder preprocessing)
    created_at = Column(DateTime, default=func.now())
    task_id = Column(Text, nullable=True)  # Task ID for LLM processing recovery


    folder = relationship("Folder", back_populates="documents")
    batch = relationship("Batch", back_populates="documents")

class Prompt(Base):
    __tablename__ = 'prompts'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_text = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    active = Column(Integer, default=1, nullable=True)  # Fixed: DB allows null
    created_at = Column(DateTime, default=func.now())  # Added: Missing column from DB



class LlmProvider(Base):
    __tablename__ = 'llm_providers'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)
    provider_type = Column(Text, nullable=False)
    default_base_url = Column(Text)
    supports_model_discovery = Column(Boolean, default=True, nullable=False)
    auth_type = Column(Text, default='api_key', nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    provider_models = relationship("ProviderModel", back_populates="provider")

class Model(Base):
    __tablename__ = 'models'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    common_name = Column(Text, unique=True, nullable=False)
    display_name = Column(Text, nullable=False)
    model_family = Column(Text)
    parameter_count = Column(Text)
    context_length = Column(Integer)
    capabilities = Column(Text)
    notes = Column(Text)
    is_globally_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

    # Relationships
    provider_models = relationship("ProviderModel", back_populates="model")
    aliases = relationship("ModelAlias", back_populates="model")

class ProviderModel(Base):
    __tablename__ = 'provider_models'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey('llm_providers.id'), nullable=False)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    provider_model_name = Column(Text, nullable=False)
    is_active = Column(Boolean, default=False, nullable=True)  # Fixed: DB allows null
    is_available = Column(Boolean, default=True, nullable=True)  # Fixed: DB allows null
    last_checked = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())

    # Relationships
    model = relationship("Model", back_populates="provider_models")
    provider = relationship("LlmProvider", back_populates="provider_models")

class ModelAlias(Base):
    __tablename__ = 'model_aliases'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    alias_name = Column(Text, nullable=False)
    provider_pattern = Column(Text)
    created_at = Column(DateTime, default=func.now())

    # Relationships
    model = relationship("Model", back_populates="aliases")

class LlmModel(Base):
    __tablename__ = 'llm_models'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey('llm_providers.id'), nullable=True)  # Fixed: DB allows null
    model_name = Column(Text, nullable=False)
    model_id = Column(Text, nullable=False)
    is_active = Column(Boolean, default=False, nullable=False)
    capabilities = Column(Text)
    last_updated = Column(DateTime, default=func.now())





class BatchArchive(Base):
    __tablename__ = 'batch_archive'
    __table_args__ = {'extend_existing': True}
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

class Connection(Base):
    """
    A Connection represents a specific instance of a provider with actual connection details.
    """
    __tablename__ = 'connections'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    provider_id = Column(Integer, ForeignKey('llm_providers.id'), nullable=False)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=True)
    base_url = Column(Text)
    api_key = Column(Text)
    port_no = Column(Integer)
    connection_config = Column(JSONB)
    is_active = Column(Boolean, default=True, nullable=False)
    connection_status = Column(Text, default='unknown', nullable=False)
    last_tested = Column(DateTime, nullable=True)
    last_test_result = Column(Text)
    supports_model_discovery = Column(Boolean, default=True, nullable=False)
    available_models = Column(Text)
    last_model_sync = Column(DateTime, nullable=True)
    notes = Column(Text)
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

    # Relationships
    provider = relationship("LlmProvider", foreign_keys=[provider_id])
    model = relationship("Model", foreign_keys=[model_id])



class Snapshot(Base):
    __tablename__ = 'snapshots'
    __table_args__ = {'extend_existing': True}

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, nullable=False)
    description = Column(Text)
    file_path = Column(Text, unique=True, nullable=False)
    file_size = Column(Integer)  # Size in bytes
    database_name = Column(Text, default='doc_eval', nullable=False)
    snapshot_type = Column(Text, default='full', nullable=False)  # full, partial, schema_only
    compression = Column(Text, default='gzip', nullable=False)  # gzip, none
    created_at = Column(DateTime, default=func.now())
    created_by = Column(Text, default='system')

    # Metadata about what was included in the snapshot
    tables_included = Column(JSONB)  # List of table names included
    record_counts = Column(JSONB)  # Count of records per table at time of snapshot
    database_version = Column(Text)  # PostgreSQL version
    application_version = Column(Text)  # Application version when snapshot was created

    # Status tracking
    status = Column(Text, default='creating', nullable=False)  # creating, completed, failed
    error_message = Column(Text)  # If status is failed

    # Additional metadata
    notes = Column(Text)
    tags = Column(JSONB)  # For categorizing snapshots
