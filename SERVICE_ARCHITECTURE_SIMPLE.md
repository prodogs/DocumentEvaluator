# DocumentEvaluator Service Layer Architecture

## Simplified Class Diagram (Mermaid 8.8.0 Compatible)

```mermaid
classDiagram
    class BaseLLMProvider {
        <<abstract>>
        +test_connection()
        +discover_models()
        +validate_config()
        +get_default_config()
    }

    class BatchService {
        +create_batch()
        +save_batch()
        +stage_batch()
        +restage_batch()
        +run_batch()
        +get_batch_progress()
        +get_staging_status()
    }

    class ConnectionService {
        +get_all_connections()
        +create_connection()
        +update_connection()
        +test_connection()
        +delete_connection()
    }

    class ModelService {
        +get_all_models()
        +create_model()
        +update_model()
        +discover_and_link_models()
    }

    class LlmProviderService {
        +get_all_providers()
        +create_provider()
        +test_connection()
        +discover_models()
    }

    class DocumentEncodingService {
        +encode_and_store_document()
        +prepare_document_for_llm()
        +batch_encode_documents()
    }

    class FolderPreprocessingService {
        +preprocess_folder()
        +preprocess_folder_async()
        +get_folder_status()
    }

    class ServiceHealthMonitor {
        +start_monitoring()
        +get_service_status()
        +get_all_service_status()
    }

    class KnowledgeQueueProcessor {
        +start_processing()
        +stop_processing()
        +get_queue_status()
        +process_document()
    }

    OllamaProvider --|> BaseLLMProvider
    OpenAIProvider --|> BaseLLMProvider
    LMStudioProvider --|> BaseLLMProvider
    AmazonProvider --|> BaseLLMProvider
    GrokProvider --|> BaseLLMProvider

    ConnectionService --> LlmProviderService
    LlmProviderService --> ModelService
    BatchService --> DocumentEncodingService
    FolderPreprocessingService --> DocumentEncodingService
    ModelService --> ModelNormalizationService
```

## Service Relationships

### Inheritance Hierarchy
- **BaseLLMProvider** (Abstract Base Class)
  - OllamaProvider
  - OpenAIProvider
  - LMStudioProvider
  - AmazonProvider
  - GrokProvider

### Service Dependencies
- **BatchService** → DocumentEncodingService
  - Uses for document preparation during staging
- **ConnectionService** → LlmProviderService
  - Uses for provider-specific operations
- **LlmProviderService** → ModelService
  - Uses for model discovery and management
- **FolderPreprocessingService** → DocumentEncodingService
  - Uses for document encoding
- **ModelService** → ModelNormalizationService
  - Uses for model name normalization

## Key Services Description

### BatchService (Unified)
The BatchService now incorporates staging functionality:
- `save_batch()` - Creates batch in SAVED status
- `stage_batch()` - Creates and stages batch in one operation
- `restage_batch()` - Re-stages existing batch
- `run_batch()` - Executes batch processing
- `get_staging_status()` - Gets current staging status

### Status Flow
```
SAVED → STAGING → STAGED → PROCESSING → COMPLETED
         ↓
    FAILED_STAGING
```

### Provider Architecture
Each provider implements the BaseLLMProvider interface:
- Connection testing
- Model discovery
- Configuration validation
- Default configuration

### Database Integration
- **Primary DB**: PostgreSQL (doc_eval)
- **Secondary DB**: PostgreSQL (KnowledgeDocuments)
- **Staging Process**: Documents encoded in doc_eval, staged to KnowledgeDocuments

## Architectural Benefits

1. **Unified BatchService**: Eliminates code duplication between batch and staging
2. **Provider Abstraction**: Easy to add new LLM providers
3. **Service Layer Pattern**: Clear separation of concerns
4. **Configuration Snapshots**: Ensures consistency across batch lifecycle
5. **Background Processing**: Health monitoring and queue processing run independently