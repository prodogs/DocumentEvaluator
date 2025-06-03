# PydanticAI Implementation

## Overview

This implementation replaces the raw RAG API calls with PydanticAI agents that provide:
- **Type-safe LLM interactions** with validated structured outputs
- **Multi-provider support** (OpenAI, Anthropic, Ollama, etc.)
- **Dependency injection** for clean service integration
- **Built-in error handling** and retry mechanisms
- **Async processing** for better performance

## Architecture

```
┌─────────────────────┐    ┌──────────────────────┐    ┌─────────────────────┐
│   BatchService      │────│ PydanticAI Queue     │────│   PydanticAI        │
│                     │    │ Processor            │    │   Agents            │
│ - get_batches()     │    │                      │    │                     │
│ - get_next_doc()    │    │ - monitor_batches()  │    │ - OpenAI Agent      │
│ - update_status()   │    │ - process_async()    │    │ - Anthropic Agent   │
│ - check_complete()  │    │ - structured_output  │    │ - Ollama Agent      │
└─────────────────────┘    └──────────────────────┘    └─────────────────────┘
```

## Key Features

### 1. Structured Output Models

```python
class DocumentAnalysis(BaseModel):
    overall_score: float = Field(ge=0, le=100, description="Quality score")
    insights: List[str] = Field(description="Key insights")
    categories: List[str] = Field(description="Document categories")
    summary: str = Field(description="Brief summary")
    sentiment: str = Field(description="positive/negative/neutral")
    tokens: TokenMetrics
    processing_time_ms: int
    confidence: float = Field(ge=0, le=1, description="Confidence score")
```

### 2. Multi-Provider Agent Support

- **OpenAI**: GPT-4, GPT-3.5-turbo
- **Anthropic**: Claude-3 Sonnet, Haiku, Opus
- **Ollama**: Llama2, Mistral, CodeLlama
- **Extensible**: Easy to add new providers

### 3. Agent Tools

```python
@agent.tool
async def calculate_quality_score(
    ctx: RunContext[ProcessingDependencies],
    content_length: int,
    readability: str,
    relevance: str
) -> float:
    """Calculate document quality score"""
    # Implementation logic
    
@agent.tool
async def extract_key_phrases(
    ctx: RunContext[ProcessingDependencies],
    text: str,
    max_phrases: int = 10
) -> List[str]:
    """Extract key phrases from text"""
    # Implementation logic
```

## Integration with Existing System

### 1. BatchService Integration

The PydanticAI processor integrates seamlessly with the existing BatchService:

```python
# Get work from BatchService
doc_info = batch_service.get_next_document_for_processing(batch_id)

# Process with PydanticAI
result = await agent.run(prompt, deps=dependencies)

# Report results back to BatchService
batch_service.update_document_status(doc_id, 'COMPLETED', response_data)
```

### 2. Structured Response Data

Instead of raw text responses, we now get structured data:

```python
response_data = {
    'response_text': analysis.summary,
    'overall_score': analysis.overall_score,
    'structured_analysis': analysis.model_dump(),
    'insights': analysis.insights,
    'categories': analysis.categories,
    'sentiment': analysis.sentiment,
    'confidence': analysis.confidence,
    'input_tokens': analysis.tokens.input_tokens,
    'output_tokens': analysis.tokens.output_tokens
}
```

## Installation Requirements

Add to `requirements.txt`:

```txt
pydantic-ai>=0.0.7
pydantic>=2.0
```

For different providers:
```txt
# OpenAI
openai>=1.0.0

# Anthropic
anthropic>=0.8.0

# Ollama (no additional deps needed)
```

## Configuration

### Environment Variables

```bash
# OpenAI
OPENAI_API_KEY=sk-...

# Anthropic
ANTHROPIC_API_KEY=ant-...

# Ollama (if not localhost)
OLLAMA_BASE_URL=http://localhost:11434
```

### Provider Configuration

The system automatically detects provider type from connection configuration:

```python
{
    "provider_type": "openai",
    "model_name": "gpt-4",
    "api_key": "sk-...",
    "base_url": "https://api.openai.com/v1"
}
```

## Usage

### Starting the PydanticAI Processor

```python
# In app.py or main startup
from services.pydantic_ai_queue_processor import start_pydantic_ai_processor

start_pydantic_ai_processor()
```

### Switching from RAG API to PydanticAI

1. **Stop existing processor**:
   ```python
   from services.knowledge_queue_processor import stop_queue_processor
   stop_queue_processor()
   ```

2. **Start PydanticAI processor**:
   ```python
   from services.pydantic_ai_queue_processor import start_pydantic_ai_processor
   start_pydantic_ai_processor()
   ```

## Benefits Over RAG API

### 1. Type Safety
- Compile-time validation of inputs/outputs
- Structured response parsing
- Reduced runtime errors

### 2. Better Error Handling
- Automatic retry with exponential backoff
- Provider-specific error handling
- Graceful degradation

### 3. Enhanced Monitoring
- Built-in token tracking
- Response time metrics
- Confidence scoring
- Provider-specific stats

### 4. Development Experience
- IntelliSense support for response fields
- Clear data models
- Easy testing with mock responses

## Migration Strategy

### Phase 1: Parallel Testing
- Run both processors simultaneously
- Compare results and performance
- Validate structured outputs

### Phase 2: Gradual Rollout
- Switch specific connection types to PydanticAI
- Monitor performance and accuracy
- Adjust agent configurations

### Phase 3: Full Migration
- Replace RAG API processor completely
- Remove legacy code
- Optimize PydanticAI configurations

## Performance Considerations

### Async Processing
- Non-blocking document processing
- Better resource utilization
- Higher throughput

### Connection Pooling
- Reuse HTTP connections
- Reduced latency
- Better reliability

### Caching
- Cache model responses for identical inputs
- Reduce API costs
- Faster repeated analyses

## Monitoring and Debugging

### Status Endpoint
```python
# Get detailed processor status
status = get_pydantic_ai_processor_status()

# Returns:
{
    'is_running': True,
    'active_tasks': 5,
    'available_agents': ['openai', 'anthropic', 'ollama'],
    'stats': {
        'processed': 150,
        'failed': 3,
        'last_activity': '2024-01-15T10:30:00Z'
    }
}
```

### Logging
- Structured logging with correlation IDs
- Performance metrics per provider
- Error categorization and alerting

## Future Enhancements

1. **Agent Routing**: Route documents to best agent based on content type
2. **Response Caching**: Cache responses for duplicate content
3. **A/B Testing**: Compare different agent configurations
4. **Cost Optimization**: Choose cheapest provider for simple tasks
5. **Quality Assurance**: Automatic validation of agent outputs

This PydanticAI implementation provides a robust, type-safe foundation for document processing while maintaining compatibility with the existing BatchService architecture.