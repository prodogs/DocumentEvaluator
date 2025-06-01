# Document Evaluator API Endpoints

## Overview

The Document Evaluator API provides endpoints for managing LLM connections, staging documents, and processing them with various LLM providers. The API has been updated to use the new connections architecture (replacing deprecated llm_configurations).

## Base URL

```text
http://localhost:5001
```

## Authentication

Currently, the API does not require authentication for local development.

## Connection Management Endpoints

### GET /api/llm-configurations

Returns a list of all connections (replaces deprecated LLM configurations).

**Response:**

```json
{
  "llm_configurations": [
    {
      "id": 1,
      "llm_name": "My Local Ollama Connection",
      "base_url": "http://studio.local",
      "model_name": "gemma3-latest",
      "api_key": null,
      "provider_type": "ollama",
      "port_no": 11434,
      "active": true
    }
  ],
  "total": 1,
  "active_count": 1
}
```

### POST /api/llm-configurations

Creates a new connection configuration.

**Request Body:**

```json
{
  "llm_name": "My New Connection",
  "base_url": "http://localhost",
  "model_name": "llama2",
  "provider_type": "ollama",
  "api_key": null,
  "port_no": 11434
}
```

**Response:**

```json
{
  "message": "Connection created successfully",
  "config": {
    "id": 2,
    "llm_name": "My New Connection",
    "base_url": "http://localhost",
    "model_name": "llama2",
    "provider_type": "ollama",
    "api_key": null,
    "port_no": 11434,
    "active": true
  }
}
```

### PUT /api/llm-configurations/{config_id}

Updates an existing connection configuration.

### DELETE /api/llm-configurations/{config_id}

Deletes a connection configuration.

### POST /api/llm-configurations/{config_id}/activate

Activates a connection for use in document processing.

### POST /api/llm-configurations/{config_id}/deactivate

Deactivates a connection to prevent its use in document processing.

### POST /api/connections/{connection_id}/test

Tests a connection by making a real RAG API call with test data.

**Response (Success):**

```json
{
  "success": true,
  "message": "Connection test successful",
  "response": {
    "task_id": "484e76d2-99a0-4e95-831c-e8148d10013e",
    "status": "queued",
    "message": "LLM analysis initiated in background"
  },
  "response_time_ms": 1234.56,
  "connection_name": "My Local Ollama Connection",
  "model_name": "gemma3-latest",
  "provider_type": "ollama"
}
```

### GET /llm-configs

Legacy endpoint that returns connections in the old format for backward compatibility.

## Prompt Management Endpoints

### GET /api/prompts

Returns a list of all prompts from the database.

**Response:**

```json
{
  "prompts": [
    {
      "id": 1,
      "prompt_text": "Summarize this document in 3 paragraphs.",
      "description": "General summary prompt",
      "active": true
    },
    {
      "id": 2,
      "prompt_text": "Extract key financial metrics from this document.",
      "description": "Financial metrics extraction",
      "active": true
    }
  ]
}
```

## Folder Management Endpoints

### GET /api/folders

Returns a list of all folders in the system.

**Response:**

```json
{
  "folders": [
    {
      "id": 1,
      "folder_path": "/path/to/documents",
      "folder_name": "Documents",
      "active": true,
      "status": "READY",
      "created_at": "2024-01-01T00:00:00Z"
    }
  ],
  "total": 1,
  "active_count": 1
}
```

### POST /api/folders/{folder_id}/activate

Activates a folder for processing.

### POST /api/folders/{folder_id}/deactivate

Deactivates a folder to prevent processing.

## Document Processing Endpoints

### POST /analyze_document_with_llm

Analyze documents with LLM configurations and prompts.

**Request:**

- Content-Type: `multipart/form-data`
- Body:
  - `file`: Document file to analyze
  - `filename`: Name of the file
  - `prompts`: JSON string with array of prompt objects
  - `llm_provider`: JSON string with LLM provider configuration
  - `meta_data`: (Optional) JSON string with metadata

**Example LLM Provider Data:**

```json
{
  "provider_type": "ollama",
  "url": "http://studio.local",
  "model_name": "gemma3-latest",
  "api_key": null,
  "port_no": 11434
}
```

**Response:**

```json
{
  "task_id": "484e76d2-99a0-4e95-831c-e8148d10013e",
  "status": "queued",
  "message": "LLM analysis initiated in background. Use /analyze_status/{task_id} to poll for results."
}
```

### GET /analyze_status/{task_id}

Get the status of a document analysis task.

**Parameters:**

- `task_id`: Task ID returned from analyze_document_with_llm

**Response:**

```json
{
  "totalDocuments": 1,
  "processedDocuments": 0,
  "outstandingDocuments": 1,
  "status": "processing",
  "progress_percentage": 0,
  "error_message": null
}
```

## Response Management Endpoints

### GET /api/llm-responses

Returns LLM responses with filtering and pagination.

**Query Parameters:**

- `limit`: Maximum number of responses to return (default: 50)
- `offset`: Number of responses to skip (default: 0)
- `status`: Filter by response status (N=New, P=Processing, C=Complete, E=Error)

**Response:**

```json
{
  "responses": [
    {
      "id": 1,
      "document_id": 123,
      "task_id": "484e76d2-99a0-4e95-831c-e8148d10013e",
      "status": "C",
      "prompt": {
        "id": 1,
        "prompt_text": "Summarize this document",
        "description": "General summary prompt"
      },
      "connection": {
        "id": 1,
        "llm_name": "My Local Ollama Connection",
        "provider_type": "ollama"
      },
      "response_text": "This document discusses...",
      "response_time_ms": 2500,
      "overall_score": 85,
      "timestamp": "2024-01-01T12:00:00Z"
    }
  ],
  "total": 1,
  "limit": 50,
  "offset": 0
}
```

## Health and Monitoring Endpoints

### GET /api/health

Check if the API is running properly.

**Response:**

```json
{
  "status": "ok",
  "version": "2.0.0",
  "swagger": "available at /api/docs"
}
```

## Error Responses

All endpoints may return error responses in the following format:

```json
{
  "error": "Error message describing what went wrong",
  "success": false
}
```

## Common HTTP Status Codes

- `200 OK`: Request successful
- `201 Created`: Resource created successfully
- `400 Bad Request`: Invalid request data
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server error

## Migration Notes

### Deprecated Endpoints

The following endpoints are deprecated but maintained for backward compatibility:

- `/llm-configs` - Use `/api/llm-configurations` instead

### Breaking Changes in v2.0.0

1. **LLM Configurations → Connections**: The underlying data model has changed from `llm_configurations` to `connections` table
2. **Field Mapping**: `base_url` in connections maps to `url` field in RAG API calls
3. **New Connection Testing**: Added `/api/connections/{id}/test` endpoint for real connection testing
4. **Enhanced Error Handling**: Improved error messages and status codes

## Swagger Documentation

Interactive API documentation is available at:

```text
http://localhost:5001/api/docs
```
