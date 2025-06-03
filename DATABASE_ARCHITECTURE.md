# Database Architecture

## Overview

The DocumentEvaluator application uses a **two-database architecture** to separate concerns and improve scalability.

## Database Naming Convention

### 1. KnowledgeSync Database (Main Application)
- **Purpose**: Main application database containing configuration and metadata
- **Location**: `postgresql://postgres:prodogs03@studio.local:5432/doc_eval`
- **Naming**: Referred to as "KnowledgeSync Database" throughout the application
- **Can reside**: Anywhere (currently at studio.local, but portable)

**Contains:**
- `batches` - Batch configurations and status
- `folders` - Document folders being processed
- `documents` - Individual document metadata
- `connections` - LLM provider connections
- `prompts` - Analysis prompts
- `models` - Available LLM models
- `llm_providers` - LLM provider configurations
- And other application configuration tables

### 2. KnowledgeDocuments Database (Processing Queue)
- **Purpose**: Processing queue and document storage
- **Location**: `postgresql://postgres:prodogs03@studio.local:5432/KnowledgeDocuments`
- **Naming**: Referred to as "KnowledgeDocuments Database" throughout the application
- **Can reside**: Anywhere (currently at studio.local, but can be on separate server)

**Contains:**
- `llm_responses` - Processing queue and LLM response data
- `docs` - Base64 encoded document content for processing

## Why Two Databases?

1. **Separation of Concerns**
   - Configuration data (KnowledgeSync) vs Processing data (KnowledgeDocuments)
   - Different access patterns and scaling requirements

2. **Scalability**
   - Processing queue can be on a high-performance server
   - Configuration database can be optimized for OLTP operations

3. **Independence**
   - Processing can continue even if configuration database is temporarily unavailable
   - Different backup and maintenance schedules

4. **Security**
   - Different access controls for configuration vs processing data
   - Processing database can be more isolated

## Connection Patterns

### Application Code
- Uses SQLAlchemy ORM to connect to KnowledgeSync Database
- Uses direct psycopg2 connections for KnowledgeDocuments Database
- Connection pooling for better performance

### Health Monitoring
Both databases are monitored separately in the health checks:
- `knowledgesync_database` - Main application database health
- `knowledge_database` - Processing queue database health

## Migration Considerations

If you need to move either database:

1. **KnowledgeSync Database**: Update `POSTGRESQL_URL` in `server/database.py`
2. **KnowledgeDocuments Database**: Update connection strings in processing services

Both databases can reside on the same server (current setup) or be distributed across different servers for better performance and scalability.