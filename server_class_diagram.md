# DocumentEvaluator Server - Class Diagram

This document provides a comprehensive class diagram of the DocumentEvaluator server architecture, showing the relationships between all major components.

## Server Architecture Overview

The DocumentEvaluator server follows a modular Flask application architecture with clear separation of concerns:

- **Flask Application Layer**: Main application entry points and configuration
- **API Layer**: REST endpoints organized by domain (batches, documents, models, etc.)
- **Service Layer**: Business logic and domain services
- **Data Layer**: Database models and data access
- **Core Infrastructure**: Database, caching, logging, middleware

## Class Diagram

```mermaid
classDiagram
    %% Flask Application Layer
    class FlaskApp {
        +create_app(config_name) Flask
        +register_blueprints(app)
        +register_cli_commands(app)
        +init_extensions(app)
        +initialize_services()
    }

    class Config {
        +APP_NAME: str
        +VERSION: str
        +SECRET_KEY: str
        +HOST: str
        +PORT: int
        +SQLALCHEMY_DATABASE_URI: str
        +REDIS_URL: str
        +init_app(app)
    }

    %% Core Infrastructure
    class DatabaseManager {
        -config: Config
        -engine: Engine
        -session_factory: sessionmaker
        -Session: scoped_session
        +init_engine() Engine
        +init_session_factory() Session
        +get_session() Session
        +session_scope() contextmanager
        +health_check() bool
        +close_all_sessions()
        +dispose_engine()
    }

    class CacheManager {
        -redis_client: Redis
        -memory_cache: Dict
        -default_timeout: int
        +get(key) Any
        +set(key, value, timeout) bool
        +delete(key) bool
        +clear() int
        +cached(timeout) decorator
    }

    class MiddlewareManager {
        +setup_request_context()
        +teardown_request_context()
        +handle_api_error(error)
        +handle_database_error(error)
        +monitor_performance(func)
        +health_check_response() Dict
    }

    %% Database Models
    class Batch {
        +id: int
        +batch_number: int
        +batch_name: str
        +status: str
        +created_at: datetime
        +started_at: datetime
        +completed_at: datetime
        +processed_documents: int
        +total_documents: int
        +config_snapshot: Dict
        +meta_data: Dict
        +folder_ids: List[int]
    }

    class Document {
        +id: int
        +batch_id: int
        +folder_id: int
        +filename: str
        +filepath: str
        +file_size: int
        +encoding_status: str
        +processing_status: str
        +task_id: str
        +created_at: datetime
        +processed_at: datetime
        +meta_data: Dict
    }

    class Folder {
        +id: int
        +folder_path: str
        +folder_name: str
        +active: bool
        +status: str
        +created_at: datetime
        +updated_at: datetime
    }

    class Connection {
        +id: int
        +name: str
        +description: str
        +provider_id: int
        +model_id: int
        +base_url: str
        +api_key: str
        +port_no: int
        +connection_config: Dict
        +is_active: bool
        +connection_status: str
        +last_tested: datetime
        +supports_model_discovery: bool
    }

    class LlmProvider {
        +id: int
        +name: str
        +provider_type: str
        +description: str
        +base_url: str
        +auth_type: str
        +supports_discovery: bool
        +is_active: bool
        +created_at: datetime
    }

    class Model {
        +id: int
        +common_name: str
        +display_name: str
        +model_family: str
        +parameter_count: str
        +context_length: int
        +capabilities: Dict
        +is_globally_active: bool
        +created_at: datetime
        +updated_at: datetime
    }

    class Prompt {
        +id: int
        +name: str
        +description: str
        +prompt_text: str
        +is_active: bool
        +created_at: datetime
        +updated_at: datetime
    }

    %% Service Layer
    class BatchService {
        +create_batch(folder_ids, connection_ids, prompt_ids, batch_name, meta_data) Dict
        +save_batch(folder_ids, connection_ids, prompt_ids, batch_name, meta_data) Dict
        +stage_batch(batch_id) Dict
        +run_batch(batch_id) Dict
        +get_batch_status(batch_id) Dict
        +get_batch_progress(batch_id) Dict
        +rerun_batch(batch_id) Dict
        +reset_batch_to_prestage(batch_id) Dict
        -_create_config_snapshot(folder_ids) Dict
        -_perform_staging(batch_id, session) Dict
    }

    class ConnectionService {
        -provider_service: LlmProviderService
        +get_all_connections() List[Dict]
        +get_connection_by_id(connection_id) Dict
        +create_connection(connection_data) Dict
        +update_connection(connection_id, connection_data) Dict
        +delete_connection(connection_id) bool
        +test_connection(connection_id) Tuple[bool, str]
        +sync_models(connection_id) Tuple[bool, str]
    }

    class ModelService {
        +get_all_models() List[Dict]
        +get_model_by_id(model_id) Dict
        +create_model(model_data) Dict
        +update_model(model_id, model_data) Dict
        +delete_model(model_id) bool
        +discover_and_link_models(provider_id) Dict
        -_model_to_dict(model) Dict
    }

    class LlmProviderService {
        -provider_adapters: Dict[str, BaseLLMProvider]
        +get_all_providers() List[Dict]
        +get_provider_by_id(provider_id) Dict
        +create_provider(provider_data) Dict
        +test_connection(provider_config) Tuple[bool, str]
        +discover_models(provider_id, provider_config) List[Dict]
        -_load_provider_adapters()
    }

    class DocumentEncodingService {
        +encode_and_store_document(document_path, batch_id) Dict
        +prepare_document_for_llm(document_id) str
        +batch_encode_documents(document_ids) List[Dict]
        +get_encoding_status(document_id) str
    }

    class FolderPreprocessingService {
        +preprocess_folder(folder_id) Dict
        +preprocess_folder_async(folder_id) str
        +get_folder_status(folder_id) Dict
        +get_preprocessing_progress(task_id) Dict
    }

    class ServiceHealthMonitor {
        -check_interval: int
        -health_checks: Dict
        -current_status: Dict
        -monitoring_thread: Thread
        +start_monitoring()
        +stop_monitoring_service()
        +get_service_status(service_name) Dict
        +get_all_service_status() Dict
        +check_service_now(service_name) bool
    }

    %% Provider Adapters
    class BaseLLMProvider {
        <<abstract>>
        +test_connection(config) Tuple[bool, str]
        +discover_models(config) List[Dict]
        +validate_config(config) bool
        +get_default_config() Dict
    }

    class OllamaProvider {
        +test_connection(config) Tuple[bool, str]
        +discover_models(config) List[Dict]
        +validate_config(config) bool
    }

    class OpenAIProvider {
        +test_connection(config) Tuple[bool, str]
        +discover_models(config) List[Dict]
        +validate_config(config) bool
    }

    class LMStudioProvider {
        +test_connection(config) Tuple[bool, str]
        +discover_models(config) List[Dict]
        +validate_config(config) bool
    }

    %% API Routes (Blueprints)
    class BatchRoutes {
        +get_batches() Response
        +get_batch_details(batch_id) Response
        +stage_analysis() Response
        +run_batch(batch_id) Response
        +delete_batch(batch_id) Response
    }

    class DocumentRoutes {
        +get_documents() Response
        +upload_document() Response
        +get_document_content(doc_id) Response
        +delete_document(doc_id) Response
    }

    class FolderRoutes {
        +list_folders() Response
        +add_folder() Response
        +update_folder(folder_id) Response
        +delete_folder(folder_id) Response
    }

    class ConnectionRoutes {
        +list_connections() Response
        +create_connection() Response
        +update_connection(connection_id) Response
        +test_connection(connection_id) Response
        +sync_connection_models(connection_id) Response
    }

    class ModelRoutes {
        +get_all_models() Response
        +create_model() Response
        +update_model(model_id) Response
        +delete_model(model_id) Response
    }

    %% Relationships
    
    %% Flask App Dependencies
    FlaskApp --> Config : uses
    FlaskApp --> DatabaseManager : initializes
    FlaskApp --> CacheManager : initializes
    FlaskApp --> MiddlewareManager : initializes

    %% Database Relationships
    Batch ||--o{ Document : contains
    Folder ||--o{ Document : stores
    Connection }o--|| LlmProvider : belongs_to
    Connection }o--|| Model : uses
    
    %% Service Dependencies
    BatchService --> DocumentEncodingService : uses
    ConnectionService --> LlmProviderService : uses
    LlmProviderService --> ModelService : uses
    LlmProviderService *-- BaseLLMProvider : provider_adapters
    
    %% Provider Inheritance
    OllamaProvider --|> BaseLLMProvider
    OpenAIProvider --|> BaseLLMProvider
    LMStudioProvider --|> BaseLLMProvider
    
    %% Route Dependencies
    BatchRoutes --> BatchService : uses
    DocumentRoutes --> DocumentEncodingService : uses
    FolderRoutes --> FolderPreprocessingService : uses
    ConnectionRoutes --> ConnectionService : uses
    ModelRoutes --> ModelService : uses
    
    %% Core Infrastructure Usage
    BatchService --> DatabaseManager : uses
    ConnectionService --> DatabaseManager : uses
    ModelService --> DatabaseManager : uses
    LlmProviderService --> CacheManager : uses
```

## Key Architecture Patterns

### 1. **Application Factory Pattern**
- `create_app()` function creates and configures Flask application instances
- Supports different configurations for development, testing, and production

### 2. **Service Layer Pattern**
- Business logic encapsulated in service classes
- Clear separation between API routes and business logic
- Services handle database operations and external integrations

### 3. **Repository Pattern**
- Database access abstracted through service layer
- SQLAlchemy models define data structure
- DatabaseManager handles connection pooling and session management

### 4. **Provider Pattern**
- `BaseLLMProvider` abstract class defines interface for LLM providers
- Concrete implementations for different providers (Ollama, OpenAI, etc.)
- `LlmProviderService` manages provider adapters

### 5. **Blueprint Pattern**
- API routes organized into Flask blueprints by domain
- Each blueprint handles specific resource types (batches, documents, etc.)

## Core Components

### **Flask Application Layer**
- **FlaskApp**: Main application factory and configuration
- **Config**: Environment-specific configuration management

### **API Layer**
- **Route Blueprints**: REST endpoints organized by domain
- **Middleware**: Request/response processing, error handling, performance monitoring

### **Service Layer**
- **BatchService**: Manages document processing batches
- **ConnectionService**: Handles LLM provider connections
- **ModelService**: Manages AI models across providers
- **DocumentEncodingService**: Handles document processing and encoding

### **Data Layer**
- **SQLAlchemy Models**: Define database schema and relationships
- **DatabaseManager**: Connection pooling and session management

### **Infrastructure**
- **CacheManager**: Redis-based caching with in-memory fallback
- **ServiceHealthMonitor**: System health monitoring and alerting
- **Logging**: Structured logging with performance metrics
