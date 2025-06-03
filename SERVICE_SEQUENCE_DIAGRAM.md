# Document Processing Workflow - Sequence Diagrams

## 1. Batch Creation and Staging

```mermaid
sequenceDiagram
    participant User
    participant API as Flask API
    participant BS as BatchService
    participant DB as PostgreSQL (doc_eval)
    participant KDB as PostgreSQL (KnowledgeDocuments)

    User->>API: POST /api/batches/save
    Note over User,API: Create batch configuration
    
    API->>BS: save_batch(folder_ids, connection_ids, prompt_ids, batch_name)
    BS->>BS: _create_config_snapshot(folder_ids)
    BS->>DB: Create Batch record (status: SAVED)
    BS->>DB: Store config_snapshot
    BS-->>API: {batch_id, status: "SAVED"}
    API-->>User: Batch created successfully

    User->>API: POST /api/batches/{id}/stage
    Note over User,API: Stage batch for processing
    
    API->>BS: stage_batch(batch_id)
    BS->>DB: Get batch and validate
    BS->>DB: Get documents from folders
    
    loop For each document
        BS->>BS: encode_document(filepath)
        BS->>KDB: INSERT INTO docs (encoded content)
        Note over BS,KDB: Create unique document_id
    end
    
    loop For each document × connection × prompt
        BS->>KDB: INSERT INTO llm_responses (status: QUEUED)
        Note over BS,KDB: Create processing tasks
    end
    
    BS->>DB: UPDATE Batch SET status = 'STAGED'
    BS-->>API: {success: true, status: "STAGED"}
    API-->>User: Batch staged for processing
```

## 2. Document Processing with BatchQueueProcessor

```mermaid
sequenceDiagram
    participant BQP as BatchQueueProcessor
    participant BS as BatchService
    participant DB as PostgreSQL (doc_eval)
    participant KDB as PostgreSQL (KnowledgeDocuments)
    participant RAG as RAG API

    Note over BQP: Background process running every 5 seconds

    loop Continuous monitoring
        BQP->>BS: get_batches_ready_for_processing()
        BS->>DB: SELECT * FROM batches WHERE status = 'STAGED'
        BS-->>BQP: List of ready batches
        
        alt Batches found
            loop For each batch (up to max_concurrent)
                BQP->>BS: get_next_document_for_processing(batch_id)
                BS->>DB: UPDATE batch status = 'PROCESSING' (if STAGED)
                BS->>KDB: SELECT llm_responses WHERE status = 'QUEUED' FOR UPDATE SKIP LOCKED
                BS->>KDB: SELECT document content from docs
                BS->>DB: GET prompt details
                BS-->>BQP: {doc_id, content, prompt, llm_config}
                
                alt Document available
                    BQP->>RAG: POST /analyze_document_with_llm
                    Note over BQP,RAG: Submit form data with doc_id, prompt, llm_config
                    RAG-->>BQP: {task_id}
                    
                    BQP->>BS: update_document_task(doc_id, task_id, "PROCESSING")
                    BS->>KDB: UPDATE llm_responses SET task_id, status = 'PROCESSING'
                    
                    Note over BQP: Track active task
                    BQP->>BQP: active_tasks[task_id] = {doc_id, batch_id, submitted_at}
                end
            end
        end
        
        Note over BQP: Check active tasks
        loop For each active task
            BQP->>RAG: GET /task_status/{task_id}
            RAG-->>BQP: {status, result}
            
            alt Task completed successfully
                BQP->>BS: update_document_status(doc_id, "COMPLETED", response_data)
                BS->>KDB: UPDATE llm_responses SET status, response_text, tokens
                BS->>DB: UPDATE batch processed_documents count
                BS->>BS: check_and_update_batch_completion(batch_id)
                
                alt All documents complete
                    BS->>DB: UPDATE batch status = 'COMPLETED', completed_at
                    Note over BS: Batch finished
                end
                
            else Task failed
                BQP->>BS: update_document_status(doc_id, "FAILED", error_data)
                BS->>KDB: UPDATE llm_responses SET status = 'FAILED', error_message
                
            else Task timeout
                BQP->>BS: update_document_status(doc_id, "TIMEOUT", timeout_data)
                BS->>KDB: UPDATE llm_responses SET status = 'TIMEOUT'
            end
            
            BQP->>BQP: Remove from active_tasks
        end
        
        BQP->>BQP: sleep(check_interval)
    end
```

## 3. Document Processing with PydanticAI

```mermaid
sequenceDiagram
    participant PAI as PydanticAIBatchProcessor
    participant BS as BatchService
    participant Agent as PydanticAI Agent
    participant LLM as LLM Provider
    participant DB as PostgreSQL (doc_eval)
    participant KDB as PostgreSQL (KnowledgeDocuments)

    Note over PAI: Async processing loop

    loop Continuous monitoring
        PAI->>BS: get_batches_ready_for_processing()
        BS-->>PAI: List of STAGED batches
        
        alt Batches found
            loop For each batch
                PAI->>BS: get_next_document_for_processing(batch_id)
                BS-->>PAI: {doc_id, content, prompt, llm_config}
                
                alt Document available
                    PAI->>BS: update_document_task(doc_id, task_id, "PROCESSING")
                    
                    Note over PAI: Create async task
                    PAI->>PAI: process_document_async(task_id, doc_info)
                    
                    PAI->>Agent: Create model for connection
                    PAI->>Agent: Set up ProcessingDependencies
                    
                    PAI->>Agent: run(prompt, deps=dependencies)
                    Agent->>LLM: API call with structured prompt
                    LLM-->>Agent: Raw response
                    Agent->>Agent: Validate response against DocumentAnalysis schema
                    Agent-->>PAI: DocumentAnalysis object
                    
                    Note over PAI: Extract structured data
                    PAI->>PAI: response_data = {
                    Note over PAI: response_text, overall_score,
                    Note over PAI: insights, categories, sentiment,
                    Note over PAI: tokens, confidence
                    Note over PAI: }
                    
                    PAI->>BS: update_document_status(doc_id, "COMPLETED", response_data)
                    BS->>KDB: UPDATE llm_responses with structured data
                    BS->>BS: check_and_update_batch_completion(batch_id)
                    
                    alt Processing error
                        PAI->>BS: update_document_status(doc_id, "FAILED", error_data)
                    end
                end
            end
        end
        
        PAI->>PAI: await asyncio.sleep(check_interval)
    end
```

## 4. Batch Rerun Process

```mermaid
sequenceDiagram
    participant User
    participant API as Flask API
    participant BS as BatchService
    participant DB as PostgreSQL (doc_eval)
    participant KDB as PostgreSQL (KnowledgeDocuments)

    User->>API: POST /api/batches/{id}/rerun
    Note over User,API: Rerun completed batch
    
    API->>BS: rerun_batch(batch_id)
    BS->>DB: Validate batch status = 'COMPLETED'
    
    BS->>KDB: DELETE FROM llm_responses WHERE batch_id = ?
    Note over BS,KDB: Clear previous results
    
    BS->>DB: Get documents and refresh encoding
    loop For each document
        BS->>KDB: INSERT/UPDATE docs (refresh encoded content)
    end
    
    BS->>DB: Get connections and prompts from config_snapshot
    loop For each document × connection × prompt
        BS->>KDB: INSERT INTO llm_responses (status: QUEUED)
    end
    
    BS->>DB: UPDATE batch status = 'STAGED'
    BS-->>API: {success: true, status: "STAGED"}
    API-->>User: Batch queued for rerun
    
    Note over KDB: Processing resumes automatically via queue processor
```

## 5. Error Handling and Recovery

```mermaid
sequenceDiagram
    participant Monitor as HealthMonitor
    participant BS as BatchService
    participant KQP as QueueProcessor
    participant KDB as KnowledgeDocuments

    Note over Monitor: Check for stuck items every 30 minutes

    Monitor->>KDB: SELECT llm_responses WHERE status = 'PROCESSING' AND started_processing_at < NOW() - INTERVAL '30 minutes'
    KDB-->>Monitor: List of stuck items
    
    alt Stuck items found
        Monitor->>KDB: UPDATE llm_responses SET status = 'QUEUED' WHERE stuck
        Note over Monitor: Reset stuck items for retry
        
        Monitor->>BS: check_and_update_batch_completion(batch_id)
        Note over BS: Recheck batch status after unsticking
    end
    
    Note over KQP: Handle connection failures
    KQP->>KQP: RAG API connection error detected
    KQP->>BS: update_document_status(doc_id, "FAILED", connection_error)
    
    Note over BS: Graceful degradation
    BS->>BS: Mark batch as degraded if too many failures
    BS->>DB: UPDATE batch with failure metrics
```

## Key Features Highlighted

### 🔄 **Atomic Operations**
- `FOR UPDATE SKIP LOCKED` prevents concurrent processing
- Single document retrieval per call
- Proper transaction boundaries

### 📊 **State Management** 
- Clear state transitions: SAVED → STAGED → PROCESSING → COMPLETED
- Real-time progress tracking
- Automatic completion detection

### 🛡️ **Error Handling**
- Timeout detection and recovery
- Stuck item reset mechanisms
- Graceful failure modes

### 🚀 **Scalability**
- Concurrent task processing
- Configurable concurrency limits
- Background processing loops

### 🎯 **Flexibility**
- Support for both RAG API and PydanticAI
- Pluggable processor architecture
- Provider-agnostic design