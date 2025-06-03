# Service State Management - State Diagrams

## 1. Batch Lifecycle States

```mermaid
stateDiagram-v2
    [*] --> CREATED: create_batch()
    
    CREATED --> SAVED: save_batch()
    SAVED --> STAGED: stage_batch()
    STAGED --> PROCESSING: first document starts
    PROCESSING --> COMPLETED: all documents done
    COMPLETED --> STAGED: rerun_batch()
    
    SAVED --> FAILED: staging error
    STAGED --> FAILED: critical error
    PROCESSING --> FAILED: unrecoverable error
    FAILED --> SAVED: reset_batch_to_prestage()
    
    state CREATED {
        [*] --> gathering_config
        gathering_config --> validating
        validating --> ready_to_save
    }
    
    state SAVED {
        [*] --> config_captured
        config_captured --> ready_for_staging
        note right of ready_for_staging: Configuration snapshot saved\nFolders, connections, prompts defined
    }
    
    state STAGED {
        [*] --> documents_encoded
        documents_encoded --> tasks_created
        tasks_created --> ready_for_processing
        note right of ready_for_processing: Documents encoded in KnowledgeDB\nLLM response tasks queued
    }
    
    state PROCESSING {
        [*] --> monitoring_queue
        monitoring_queue --> processing_documents
        processing_documents --> checking_completion
        checking_completion --> monitoring_queue: more work
        checking_completion --> finalizing: all done
        finalizing --> [*]
        
        note right of processing_documents: Queue processor active\nDocuments being analyzed
    }
    
    state COMPLETED {
        [*] --> results_available
        results_available --> archived
        note right of results_available: All responses collected\nMetrics calculated\nReady for rerun
    }
    
    state FAILED {
        [*] --> error_logged
        error_logged --> awaiting_intervention
        note right of awaiting_intervention: Manual investigation needed\nCan be reset to retry
    }
```

## 2. Document Processing States

```mermaid
stateDiagram-v2
    [*] --> CREATED: document discovered
    
    CREATED --> ENCODING: stage_batch()
    ENCODING --> ENCODED: encoding success
    ENCODING --> ENCODING_FAILED: encoding error
    
    ENCODED --> QUEUED: tasks created
    QUEUED --> PROCESSING: task submitted
    PROCESSING --> COMPLETED: task success
    PROCESSING --> FAILED: task error
    PROCESSING --> TIMEOUT: task timeout
    
    COMPLETED --> QUEUED: rerun_batch()
    FAILED --> QUEUED: retry
    TIMEOUT --> QUEUED: retry
    PROCESSING --> QUEUED: stuck reset
    
    state CREATED {
        [*] --> file_discovered
        file_discovered --> metadata_extracted
        metadata_extracted --> ready_for_encoding
    }
    
    state ENCODING {
        [*] --> reading_file
        reading_file --> base64_encoding
        base64_encoding --> validation
        validation --> storing_knowledgedb
        storing_knowledgedb --> [*]
    }
    
    state QUEUED {
        [*] --> waiting_for_processor
        waiting_for_processor --> selected_for_processing
        note right of selected_for_processing: Atomic selection with\nFOR UPDATE SKIP LOCKED
    }
    
    state PROCESSING {
        [*] --> submitting_to_llm
        submitting_to_llm --> waiting_for_response
        waiting_for_response --> receiving_result
        receiving_result --> [*]
        
        waiting_for_response --> timeout_detected: > 30 min
        timeout_detected --> [*]
    }
    
    state COMPLETED {
        [*] --> response_received
        response_received --> tokens_counted
        tokens_counted --> score_calculated
        score_calculated --> stored
        note right of stored: Full analysis available\nStructured data stored
    }
    
    state FAILED {
        [*] --> error_categorized
        error_categorized --> logged
        logged --> retryable_assessed
        note right of retryable_assessed: Error details preserved\nCan be retried
    }
```

## 3. Queue Processor States

```mermaid
stateDiagram-v2
    [*] --> STOPPED: initialization
    
    STOPPED --> STARTING: start()
    STARTING --> RUNNING: thread started
    RUNNING --> STOPPING: stop()
    STOPPING --> STOPPED: thread joined
    
    state RUNNING {
        [*] --> monitoring
        monitoring --> checking_batches
        checking_batches --> processing_work: work found
        processing_work --> checking_tasks
        checking_tasks --> monitoring: cycle complete
        checking_batches --> monitoring: no work
        
        state checking_batches {
            [*] --> query_batch_service
            query_batch_service --> evaluate_capacity
            evaluate_capacity --> select_documents: under limit
            evaluate_capacity --> skip: at limit
            select_documents --> submit_to_llm
            submit_to_llm --> track_active
            track_active --> [*]
            skip --> [*]
        }
        
        state checking_tasks {
            [*] --> poll_active_tasks
            poll_active_tasks --> update_status
            update_status --> report_results
            report_results --> cleanup_completed
            cleanup_completed --> [*]
        }
    }
    
    note right of RUNNING: Background thread\nContinuous monitoring\nNon-blocking operations
```

## 4. PydanticAI Agent States

```mermaid
stateDiagram-v2
    [*] --> INITIALIZING: processor start
    
    INITIALIZING --> READY: agents created
    READY --> PROCESSING: document received
    PROCESSING --> VALIDATING: LLM response
    VALIDATING --> COMPLETED: validation success
    VALIDATING --> FAILED: validation error
    COMPLETED --> READY: result reported
    FAILED --> READY: error reported
    
    state INITIALIZING {
        [*] --> creating_agents
        creating_agents --> registering_tools
        registering_tools --> setting_models
        setting_models --> [*]
        
        note right of creating_agents: OpenAI, Anthropic, Ollama agents\nSystem prompts configured
    }
    
    state PROCESSING {
        [*] --> preparing_dependencies
        preparing_dependencies --> calling_agent
        calling_agent --> waiting_llm_response
        waiting_llm_response --> [*]
        
        note right of calling_agent: Type-safe agent execution\nStructured prompt formatting
    }
    
    state VALIDATING {
        [*] --> schema_validation
        schema_validation --> field_validation
        field_validation --> business_rules
        business_rules --> [*]
        
        note right of schema_validation: Pydantic model validation\nType checking\nField constraints
    }
    
    state COMPLETED {
        [*] --> extracting_metrics
        extracting_metrics --> formatting_response
        formatting_response --> updating_batch_service
        updating_batch_service --> [*]
        
        note right of formatting_response: DocumentAnalysis object\nTokenMetrics included\nStructured insights
    }
```

## 5. Error Recovery Flow

```mermaid
stateDiagram-v2
    [*] --> MONITORING: health check starts
    
    MONITORING --> HEALTHY: all systems ok
    MONITORING --> DEGRADED: some issues
    MONITORING --> UNHEALTHY: critical issues
    
    HEALTHY --> MONITORING: continue monitoring
    
    DEGRADED --> INVESTIGATING: automatic diagnosis
    INVESTIGATING --> RECOVERING: fixable issue
    INVESTIGATING --> ESCALATING: manual intervention needed
    RECOVERING --> HEALTHY: recovery successful
    RECOVERING --> UNHEALTHY: recovery failed
    ESCALATING --> UNHEALTHY: awaiting manual fix
    
    UNHEALTHY --> INVESTIGATING: retry diagnosis
    UNHEALTHY --> MONITORING: manual recovery
    
    state DEGRADED {
        [*] --> stuck_tasks_detected
        [*] --> slow_responses_detected
        [*] --> high_failure_rate_detected
        
        stuck_tasks_detected --> resetting_stuck_items
        slow_responses_detected --> adjusting_timeouts
        high_failure_rate_detected --> analyzing_errors
        
        resetting_stuck_items --> [*]
        adjusting_timeouts --> [*]
        analyzing_errors --> [*]
    }
    
    state RECOVERING {
        [*] --> unsticking_items
        unsticking_items --> requeuing_failed
        requeuing_failed --> restarting_processors
        restarting_processors --> validating_recovery
        validating_recovery --> [*]
        
        note right of unsticking_items: Reset PROCESSING → QUEUED\nClear stale task_ids
    }
    
    state UNHEALTHY {
        [*] --> alerting
        alerting --> logging_details
        logging_details --> awaiting_intervention
        
        note right of awaiting_intervention: Database connectivity lost\nRAG API unreachable\nCritical service failure
    }
```

## Key State Management Features

### 🔄 **Atomic Transitions**
- Single responsibility per state change
- Transactional consistency
- Rollback capability

### 📊 **Progress Tracking**
- Real-time state visibility
- Progress percentage calculation
- ETA estimation

### 🛡️ **Error Resilience**
- Graceful degradation paths
- Automatic recovery mechanisms
- Manual intervention points

### 🚀 **Scalable Design**
- Concurrent state management
- Lock-free where possible
- Horizontal scaling ready

### 🎯 **Observability**
- State transition logging
- Metrics collection
- Health monitoring

These state diagrams show how the implemented architecture maintains clear, predictable state management throughout the document processing lifecycle.