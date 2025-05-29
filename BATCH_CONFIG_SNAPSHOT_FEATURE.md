# Batch Configuration Snapshot Feature

## Overview

The Batch Configuration Snapshot feature provides complete state preservation for document processing batches. When a batch is created, the system now captures a complete snapshot of all configurations, ensuring that batches are self-contained and immune to future changes in LLM configurations, prompts, or folder settings.

## Key Benefits

### 🔒 **State Preservation**
- **Complete Configuration Capture**: Every batch now stores the exact LLM configurations, prompts, and folder details that were active at batch creation time
- **Immunity to Changes**: Future modifications to LLM configs, prompts, or folders won't affect existing batches
- **Audit Trail**: Complete historical record of what configurations were used for each batch

### 📊 **Enhanced Traceability**
- **Reproducible Results**: Batches can be analyzed with the exact configurations that were used during processing
- **Configuration Comparison**: Easy comparison of configurations between different batches
- **Historical Analysis**: Understanding how configuration changes affected processing over time

### 🛡️ **Data Integrity**
- **Self-Contained Batches**: Each batch contains everything needed to understand its processing context
- **Protection from Deletions**: Even if LLM configs or prompts are deleted, batch history is preserved
- **Consistent Evaluation**: Batch results can be properly evaluated regardless of current system state

## Technical Implementation

### Database Schema Changes

#### New Column Added to `batches` Table:
```sql
ALTER TABLE batches ADD COLUMN config_snapshot JSONB;
```

#### Config Snapshot Structure:
```json
{
  "version": "1.0",
  "created_at": "2025-05-29T12:34:30.909838",
  "llm_configurations": [
    {
      "id": 1,
      "llm_name": "gemma3:27b",
      "base_url": "http://studio.local:11434",
      "model_name": "qwen2.5",
      "api_key": "...",
      "provider_type": "ollama",
      "port_no": 11434,
      "active": 1
    }
  ],
  "prompts": [
    {
      "id": 1,
      "prompt_text": "Summarize the following document:",
      "description": "Basic document summarization",
      "active": 1
    }
  ],
  "folders": [
    {
      "id": 1,
      "folder_path": "/path/to/documents",
      "folder_name": "Sample Documents",
      "active": 1,
      "created_at": "2025-05-29T10:00:00"
    }
  ],
  "documents": [
    {
      "filepath": "/path/to/document.pdf",
      "filename": "document.pdf",
      "folder_id": 1,
      "relative_path": "document.pdf",
      "file_size": 1024000,
      "discovered_at": "2025-05-29T12:34:30"
    }
  ],
  "summary": {
    "total_llm_configs": 2,
    "total_prompts": 3,
    "total_folders": 2,
    "total_documents": 58,
    "expected_combinations": 348
  }
}
```

### Code Changes

#### 1. **Model Updates** (`server/models.py`)
- Added `config_snapshot` column to `Batch` model
- Marked `folder_ids` as deprecated (maintained for backward compatibility)

#### 2. **Batch Service Enhancement** (`server/services/batch_service.py`)
- New `_create_config_snapshot()` method captures complete state
- Updated `create_multi_folder_batch()` to generate snapshots
- Automatic document discovery at batch creation time

#### 3. **API Endpoints** (`server/api/batch_routes.py`)
- New endpoint: `GET /api/batches/{batch_id}/config-snapshot`
- Returns complete configuration snapshot for analysis

#### 4. **Migration Script** (`server/migrate_batch_config_snapshot.py`)
- Adds `config_snapshot` column to existing databases
- Migrates existing batches to use configuration snapshots

## API Usage

### Get Config Snapshot for a Batch
```bash
curl "http://localhost:5001/api/batches/65/config-snapshot"
```

**Response:**
```json
{
  "success": true,
  "batch_id": 65,
  "batch_name": "Config Snapshot Test Batch",
  "batch_number": 10,
  "config_snapshot": {
    "version": "1.0",
    "created_at": "2025-05-29T12:34:30.909838",
    "llm_configurations": [...],
    "prompts": [...],
    "folders": [...],
    "documents": [...],
    "summary": {
      "total_llm_configs": 2,
      "total_prompts": 3,
      "total_folders": 2,
      "total_documents": 58,
      "expected_combinations": 348
    }
  }
}
```

## Migration and Backward Compatibility

### Automatic Migration
- The migration script automatically adds the `config_snapshot` column
- Existing batches are migrated to include configuration snapshots
- No data loss or service interruption

### Backward Compatibility
- `folder_ids` column is maintained during transition period
- Existing code continues to work without modification
- Gradual migration path for dependent systems

### Future Deprecation Path
- `folder_ids` column can be safely removed in future versions
- All batch information is now contained in `config_snapshot`
- Clean separation of concerns between batch data and configuration state

## Testing

### Verification Script
Run the test script to verify functionality:
```bash
python3 test_config_snapshot.py
```

### Expected Output
```
✅ Config snapshot functionality test PASSED!
   ✅ Batches now store complete configuration state
   ✅ Protected from future changes to LLM configs, prompts, and folders
   ✅ folder_ids column can be deprecated in future
```

## Security Considerations

### API Key Storage
- LLM configuration API keys are stored in the snapshot
- Consider implementing encryption for sensitive data
- Review access controls for config snapshot endpoints

### Data Size
- Config snapshots may increase database storage requirements
- Monitor database growth and implement archival strategies if needed
- Consider compression for large document lists

## Future Enhancements

### Potential Improvements
1. **Snapshot Compression**: Compress large document lists to reduce storage
2. **Selective Snapshots**: Option to exclude certain data from snapshots
3. **Snapshot Comparison**: Tools to compare configurations between batches
4. **Configuration Rollback**: Ability to restore configurations from snapshots
5. **Encryption**: Encrypt sensitive data in snapshots

### Integration Opportunities
1. **Batch Analysis Tools**: Enhanced reporting using historical configurations
2. **Configuration Management**: Track configuration changes over time
3. **Performance Analysis**: Correlate configuration changes with performance metrics
4. **Compliance Reporting**: Complete audit trails for regulatory requirements

## Conclusion

The Batch Configuration Snapshot feature provides robust state preservation for document processing batches, ensuring data integrity, traceability, and protection from configuration changes. This enhancement makes the system more reliable and suitable for production environments where configuration stability and audit trails are critical.
