# Document Evaluator API v2.0.0

## 🚀 Quick Start

The Document Evaluator API provides a comprehensive solution for document analysis using various LLM providers. The API has been completely updated in v2.0.0 to use the new connections architecture.

### Base URL
```
http://localhost:5001
```

### Interactive Documentation
Access the Swagger UI at: **http://localhost:5001/api/docs**

## 📋 Key Features

- **Connection Management**: Create and manage LLM provider connections (Ollama, OpenAI, Anthropic, etc.)
- **Document Processing**: Analyze documents with multiple LLM providers and prompts
- **Real-time Testing**: Test connections with actual RAG API calls
- **Status Monitoring**: Track processing progress and results
- **Backward Compatibility**: Legacy endpoints maintained for smooth migration

## 🔧 Major Changes in v2.0.0

### ✅ New Features
- **Connections Architecture**: Replaced deprecated `llm_configurations` with robust `connections` system
- **Real Connection Testing**: `/api/connections/{id}/test` endpoint makes actual RAG API calls
- **Enhanced Error Handling**: Better error messages and status codes
- **Comprehensive Documentation**: Full OpenAPI 3.0 specification with examples

### 🔄 Migration Guide
- **Endpoint Changes**: `/llm-configs` → `/api/llm-configurations` (legacy endpoint maintained)
- **Data Model**: `llm_configurations` table → `connections` table
- **Field Mapping**: `base_url` → `url` for RAG API compatibility

## 📚 Documentation

1. **[Complete API Reference](api_endpoints.md)** - Detailed endpoint documentation
2. **[OpenAPI Specification](openapi.json)** - Machine-readable API spec
3. **[Swagger UI](http://localhost:5001/api/docs)** - Interactive documentation

## 🧪 Testing the API

### Health Check
```bash
curl http://localhost:5001/api/health
```

### List Connections
```bash
curl http://localhost:5001/api/llm-configurations
```

### Test a Connection
```bash
curl -X POST http://localhost:5001/api/connections/1/test
```

## 🔗 Key Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/health` | GET | Health check |
| `/api/llm-configurations` | GET | List connections |
| `/api/llm-configurations` | POST | Create connection |
| `/api/connections/{id}/test` | POST | Test connection |
| `/analyze_document_with_llm` | POST | Analyze document |
| `/analyze_status/{task_id}` | GET | Check analysis status |
| `/api/llm-responses` | GET | List LLM responses |

## 🛠️ Development

The API is built with:
- **Flask** - Web framework
- **SQLAlchemy** - Database ORM
- **OpenAPI 3.0** - API specification
- **Swagger UI** - Interactive documentation

## 📞 Support

For issues or questions:
- Check the [API documentation](api_endpoints.md)
- Review the [OpenAPI specification](openapi.json)
- Use the [Swagger UI](http://localhost:5001/api/docs) for testing

---

**Version**: 2.0.0  
**Last Updated**: December 2024  
**Compatibility**: Maintains backward compatibility with v1.x endpoints
