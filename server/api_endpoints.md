# Document Processor API Endpoints

## Configuration Endpoints

### GET /llm-configs

Returns a list of all LLM configurations from the database.

**Response:**

```json
{
  "llmConfigs": [
    {
      "id": 1,
      "llm_name": "OpenAI GPT-4",
      "base_url": "https://api.openai.com",
      "model_name": "gpt-4",
      "api_key": "sk-...",
      "provider_type": "openai",
      "port_no": null
    },
    {
      "id": 2,
      "llm_name": "Local Ollama",
      "base_url": "http://localhost",
      "model_name": "llama2",
      "api_key": null,
      "provider_type": "ollama",
      "port_no": 11434
    }
  ]
}
```

### GET /api/prompts

Returns a list of all prompts from the database.

**Response:**

```json
{
  "prompts": [
    {
      "id": 1,
      "prompt_text": "Summarize this document in 3 paragraphs.",
      "description": "General summary prompt"
    },
    {
      "id": 2,
      "prompt_text": "Extract key financial metrics from this document.",
      "description": "Financial metrics extraction"
    }
  ]
}
```

## Document Processing Endpoints

### POST /api/process-folder

Process files uploaded in a multipart request.

**Request:**

- Content-Type: `multipart/form-data`
- Body: Files to be processed

**Response:**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "message": "Started processing 2 files with 3 LLM configurations and 2 prompts.",
  "totalFiles": 12
}
```

### POST /analyze_document_with_llm

Analyze documents with LLM configurations and prompts.

**Request:**

- Content-Type: `multipart/form-data`
- Body:
  - `files`: Array of files to analyze
  - `prompts`: Array of prompt objects
  - `llm_provider`: LLM provider configuration

**Response:**

```json
{
  "message": "Started processing 1 document-LLM-prompt combinations from uploaded files.",
  "totalFiles": 1,
  "task_id": "550e8400-e29b-41d4-a716-446655440000"
}
```

## Status Endpoints

### GET /process_status/{task_id}

Get the status of a processing task.

**Parameters:**

- `task_id`: Task ID returned from a processing request

**Response:**

```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "PROCESSING",
  "progress": 50,
  "total_files": 12,
  "processed_files": 6
}
```

### GET /api/health

Check if the API is running properly.

**Response:**

```json
{
  "status": "ok",
  "version": "1.0.0"
}
```

## Progress Monitoring

### GET /api/progress

Get current processing progress.

**Response:**

```json
{
  "totalDocuments": 12,
  "processedDocuments": 8,
  "outstandingDocuments": 4,
  "progress": 66
}
```

### GET /api/errors

Get a list of processing errors.

**Response:**

```json
{
  "errors": [
    {
      "filename": "document1.pdf",
      "llm_name": "OpenAI GPT-4",
      "prompt_text": "Summarize this document",
      "error_message": "API request timed out",
      "timestamp": "2023-05-28T14:45:32"
    }
  ]
}
```
