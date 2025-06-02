# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

DocumentEvaluator is a document analysis system that processes documents in batches using configurable LLM services. It features a two-stage batch processing workflow with real-time monitoring.

## Essential Commands

### Backend Development
```bash
# Setup
cd server
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt

# Run server (ALWAYS use app.py, not app_launcher.py)
python app.py  # Runs on http://localhost:5001

# Database migrations
alembic upgrade head  # Apply migrations
alembic revision -m "description"  # Create new migration
```

### Frontend Development
```bash
# Setup
cd client
npm install

# Development
npm run dev  # Runs on http://localhost:5173

# Build & Lint
npm run build
npm run lint
```

## Key Architecture

### Database
- PostgreSQL primary database: `postgres:prodogs03@studio.local:5432/doc_eval`
- SQLAlchemy ORM with Alembic migrations
- Models defined in `server/models.py`

### Backend Structure
- Flask REST API with modular blueprints in `server/api/`
- Service layer pattern in `server/services/`
- Provider abstraction for LLM integrations in `server/services/providers/`
- Dynamic processing queue with 30 concurrent slots
- Two-stage batch processing: PREPARED → PROCESSING → COMPLETED

### Frontend Structure
- React + Vite SPA with component-based architecture
- Main components in `client/src/components/`
- Tab-based navigation system
- Real-time updates via polling

### API Endpoints
- Swagger UI documentation at `/api/docs`
- Key endpoints:
  - `/api/batches` - Batch management
  - `/api/folders` - Folder configuration  
  - `/api/models` - Model management
  - `/api/connections` - LLM connections
  - `/api/maintenance/snapshots` - System snapshots

### Processing Flow
1. Stage 1: Create batch, encode documents, capture configuration snapshot
2. Stage 2: User-initiated processing with real-time progress tracking
3. Background task recovery on service restart
4. Token metrics tracking for all LLM responses

## Important Notes
- Always use `app.py` as the server entry point
- PostgreSQL is required (no SQLite fallback)
- Configuration snapshots ensure consistency across batch lifecycle
- Health monitoring available at `/api/health`
- Logs output to both stdout and `app.log`

## MCP Server Configuration

For Docker-based MCP server integration, use the following configuration:

```json
{
  "mcpServers": {
    "my_docker_mcp_server": {
      "command": "docker",
      "args": [
        "run",
        "-d", // Run in detached mode
        "--rm", // Remove container on exit
        "my_docker_mcp_image_name"
      ]
    }
  }
}
```