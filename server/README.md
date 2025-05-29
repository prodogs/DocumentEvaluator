# Document Processor API

This API provides endpoints for processing documents with LLMs and prompts.

## Setup

1. Create a virtual environment:

```bash
python -m venv venv
source venv/bin/activate  # On Windows, use: venv\Scripts\activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Configure the environment variables:

```bash
cp .env.example .env
# Edit .env with your configuration
```

## Running the API

```bash
# Make the launcher script executable
chmod +x launch_service.sh

# Run the service
./launch_service.sh
```

Or run manually:

```bash
python app_launcher.py
```

## API Documentation

Access the Swagger UI at: http://localhost:5001/api/docs

## Endpoints

### `/api/process-folder` (POST)

Process files uploaded in a multipart request.

### `/process_status/{task_id}` (GET)

Get the status of a processing task.

### `/analyze_document_with_llm` (POST)

Analyze documents with LLM configurations and prompts.

### `/api/health` (GET)

Check if the API is running properly.

## Database

The API uses a SQLite database (`llm_evaluation.db`) with the following tables:

- `folders`: Stores folder paths that have been processed
- `documents`: Stores document information
- `prompts`: Stores LLM prompts
- `llm_configurations`: Stores LLM configuration details
- `llm_responses`: Stores LLM processing results
