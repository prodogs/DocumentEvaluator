from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, JSON, LargeBinary, Float, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from database import Base

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
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    folder_path = Column(Text, unique=True, nullable=False)
    folder_name = Column(Text)
    active = Column(Integer, default=1, nullable=False)  # 0 = inactive, 1 = active
    status = Column(Text, default='NOT_PROCESSED', nullable=False)  # NOT_PROCESSED, PREPROCESSING, READY, ERROR
    created_at = Column(DateTime, default=func.now())

    documents = relationship("Document", back_populates="folder")

class Doc(Base):
    """Table to store encoded document content"""
    __tablename__ = 'docs'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(Integer, ForeignKey('documents.id'), nullable=False)  # Link to document
    content = Column(LargeBinary, nullable=False)  # Base64 encoded document content
    content_type = Column(Text, nullable=True)  # MIME type of the document
    doc_type = Column(Text, nullable=True)  # Document type/extension (e.g., 'pdf', 'docx', 'txt')
    file_size = Column(Integer, nullable=True)  # Original file size in bytes
    encoding = Column(Text, default='base64', nullable=False)  # Encoding method used
    created_at = Column(DateTime, default=func.now())

    # Relationship to document
    document = relationship("Document", back_populates="docs")

class Document(Base):
    __tablename__ = 'documents'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    filepath = Column(Text, unique=True, nullable=False)
    filename = Column(Text, nullable=False)
    folder_id = Column(Integer, ForeignKey('folders.id'), nullable=True)
    batch_id = Column(Integer, ForeignKey('batches.id'), nullable=True)  # Link to batch
    meta_data = Column(JSON, default={'meta_data': 'NONE'}, nullable=False)  # Document-level metadata
    valid = Column(Text, default='Y', nullable=False)  # Y = valid, N = invalid (for folder preprocessing)
    created_at = Column(DateTime, default=func.now())
    task_id = Column(Text, nullable=True)  # Task ID for LLM processing recovery

    llm_responses = relationship("LlmResponse", back_populates="document")
    folder = relationship("Folder", back_populates="documents")
    batch = relationship("Batch", back_populates="documents")
    docs = relationship("Doc", back_populates="document")

class Prompt(Base):
    __tablename__ = 'prompts'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    prompt_text = Column(Text, unique=True, nullable=False)
    description = Column(Text)
    active = Column(Integer, default=1, nullable=False)  # 0 = inactive, 1 = active

    llm_responses = relationship("LlmResponse", back_populates="prompt")

class LlmProvider(Base):
    __tablename__ = 'llm_providers'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(Text, unique=True, nullable=False)
    provider_type = Column(Text, nullable=False)  # ollama, openai, lmstudio, amazon, grok
    default_base_url = Column(Text)
    supports_model_discovery = Column(Boolean, default=True, nullable=False)
    auth_type = Column(Text, default='api_key', nullable=False)  # api_key, oauth, none
    notes = Column(Text)  # User notes about the provider
    created_at = Column(DateTime, default=func.now())

    configurations = relationship("LlmConfiguration", back_populates="provider")
    models = relationship("LlmModel", back_populates="provider")  # Legacy relationship
    provider_models = relationship("ProviderModel", back_populates="provider")  # New relationship

# New Model Architecture
class Model(Base):
    __tablename__ = 'models'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    common_name = Column(Text, unique=True, nullable=False)  # Standardized model name
    display_name = Column(Text, nullable=False)  # Human-readable name
    notes = Column(Text)  # User notes about the model
    model_family = Column(Text)  # GPT, Claude, LLaMA, etc.
    parameter_count = Column(Text)  # 7B, 13B, 70B, etc.
    context_length = Column(Integer)  # Context window size
    capabilities = Column(Text)  # JSON string of capabilities
    is_globally_active = Column(Boolean, default=True, nullable=False)  # Global activation status
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

    # Relationships
    provider_models = relationship("ProviderModel", back_populates="model")
    aliases = relationship("ModelAlias", back_populates="model")
    configurations = relationship("LlmConfiguration", back_populates="model")

class ProviderModel(Base):
    __tablename__ = 'provider_models'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey('llm_providers.id'), nullable=False)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    provider_model_name = Column(Text, nullable=False)  # Provider's name for this model
    is_active = Column(Boolean, default=False, nullable=False)
    is_available = Column(Boolean, default=True, nullable=False)
    last_checked = Column(DateTime, default=func.now())
    created_at = Column(DateTime, default=func.now())

    # Relationships
    provider = relationship("LlmProvider", back_populates="provider_models")
    model = relationship("Model", back_populates="provider_models")

class ModelAlias(Base):
    __tablename__ = 'model_aliases'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)
    alias_name = Column(Text, nullable=False)
    provider_pattern = Column(Text)  # Optional pattern to match provider-specific naming
    created_at = Column(DateTime, default=func.now())

    # Relationships
    model = relationship("Model", back_populates="aliases")

# Legacy model for backward compatibility
class LlmModel(Base):
    __tablename__ = 'llm_models'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)
    provider_id = Column(Integer, ForeignKey('llm_providers.id'), nullable=False)
    model_name = Column(Text, nullable=False)
    model_id = Column(Text, nullable=False)  # Provider-specific model identifier
    is_active = Column(Boolean, default=False, nullable=False)
    capabilities = Column(JSON, nullable=True)  # Model capabilities (context_length, etc.)
    last_updated = Column(DateTime, default=func.now())

    provider = relationship("LlmProvider", back_populates="models")

class LlmConfiguration(Base):
    __tablename__ = 'llm_configurations'
    __table_args__ = {'extend_existing': True}
    id = Column(Integer, primary_key=True, autoincrement=True)

    # Configuration identification
    name = Column(Text, unique=True, nullable=False)  # User-friendly name (e.g., "Fast Chat", "Deep Analysis")
    description = Column(Text)  # User description of this configuration

    # Three-entity relationships
    model_id = Column(Integer, ForeignKey('models.id'), nullable=False)  # Which model to use
    provider_id = Column(Integer, ForeignKey('llm_providers.id'), nullable=False)  # Which provider to use
    provider_model_id = Column(Integer, ForeignKey('provider_models.id'), nullable=False)  # Specific provider-model relationship

    # Configuration settings
    temperature = Column(Float, default=0.7)
    max_tokens = Column(Integer, default=1000)
    system_prompt = Column(Text)
    user_notes = Column(Text)  # User notes about this configuration

    # Status and metadata
    is_active = Column(Boolean, default=True, nullable=False)
    configuration_type = Column(Text, default='batch', nullable=False)  # batch, interactive, etc.
    created_at = Column(DateTime, default=func.now())
    updated_at = Column(DateTime, default=func.now())

    # Legacy fields (for backward compatibility)
    llm_name = Column(Text)  # Keep for existing data
    base_url = Column(Text)
    model_name = Column(Text)
    api_key = Column(Text)
    provider_type = Column(Text)
    port_no = Column(Integer)
    active = Column(Integer, default=1, nullable=False)  # 0 = inactive, 1 = active
    available_models = Column(JSON, nullable=True)
    model_discovery_enabled = Column(Boolean, default=True, nullable=False)
    last_model_sync = Column(DateTime, nullable=True)
    connection_status = Column(Text, default='unknown', nullable=False)
    provider_config = Column(JSON, nullable=True)

    # Relationships
    model = relationship("Model", back_populates="configurations")
    provider = relationship("LlmProvider", back_populates="configurations")
    provider_model = relationship("ProviderModel")
    llm_responses = relationship("LlmResponse", foreign_keys="LlmResponse.llm_config_id", back_populates="llm_config")

class LlmResponse(Base):
    __tablename__ = 'llm_responses'
    __table_args__ = {'extend_existing': True}
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
    overall_score = Column(Float, nullable=True)  # Suitability score (0-100) for LLM readiness
    timestamp = Column(DateTime, default=func.now())

    document = relationship("Document", back_populates="llm_responses")
    prompt = relationship("Prompt", back_populates="llm_responses")
    llm_config = relationship("LlmConfiguration", foreign_keys=[llm_config_id], back_populates="llm_responses")

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
