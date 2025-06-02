# LLM Response Cleanup - FIXED

## Issue Identified

The LLM response records in the KnowledgeDocuments database were **NOT being properly deleted** during batch reset and rerun operations, causing:

1. **Accumulating responses**: Multiple generations of responses building up
2. **Inconsistent state**: Old failed responses mixed with new ones  
3. **Processing confusion**: External system might process stale responses

## Root Cause

### ❌ Reset to Prestage (Before Fix)
- **Missing cleanup**: `reset_batch_to_prestage()` did NOT delete LLM responses
- **Only reset local state**: Batch status, document assignments
- **Left orphaned responses**: All LLM responses remained in KnowledgeDocuments

### ⚠️ Rerun Analysis (Partial Issue)
- **Basic delete present**: Had delete statement but no verification
- **No confirmation**: Didn't verify all responses were actually deleted
- **Timing issues**: Possible race conditions with external system

## Fixes Implemented

### ✅ Enhanced Reset to Prestage

**Added comprehensive LLM response cleanup:**

```python
# Step 1: Delete ALL LLM responses from KnowledgeDocuments
kb_cursor.execute("DELETE FROM llm_responses WHERE batch_id = %s", (batch_id,))
deleted_responses = kb_cursor.rowcount
logger.info(f"🗑️ RESET: Deleted {deleted_responses} LLM responses")

# Step 2: Reset batch to SAVED state  
batch.status = 'SAVED'
batch.started_at = None
batch.completed_at = None
batch.processed_documents = 0

# Step 3: Unassign documents for re-staging
for document in documents:
    document.batch_id = None
```

### ✅ Enhanced Rerun Analysis

**Added verification and robust deletion:**

```python
# Count existing responses
kb_cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE batch_id = %s", (batch_id,))
before_count = kb_cursor.fetchone()[0]

# Delete all responses  
kb_cursor.execute("DELETE FROM llm_responses WHERE batch_id = %s", (batch_id,))
deleted_responses = kb_cursor.rowcount

# Verify deletion succeeded
kb_cursor.execute("SELECT COUNT(*) FROM llm_responses WHERE batch_id = %s", (batch_id,))
after_count = kb_cursor.fetchone()[0]

if after_count > 0:
    # Retry deletion if needed
    logger.warning(f"⚠️ {after_count} responses still remain, retrying...")
```

## Testing Results

### ✅ Reset to Prestage Test
```bash
curl -X POST http://localhost:5001/api/batches/70/reset-to-prestage
```

**Result:**
```json
{
  "success": true,
  "deleted_responses": 24,
  "documents_unassigned": 8,
  "original_status": "PAUSED", 
  "new_status": "SAVED"
}
```

**Verification:** 0 LLM responses remaining ✅

### ✅ Rerun Analysis Test
```bash
curl -X POST http://localhost:5001/api/batches/70/rerun
```

**First run (no existing responses):**
```json
{
  "success": true,
  "deleted_responses": 0,
  "created_responses": 8
}
```

**Second run (with existing responses):**
```json
{
  "success": true, 
  "deleted_responses": 8,
  "created_responses": 8
}
```

## Benefits

### ✅ Clean State Management
- **Complete cleanup**: All LLM responses properly deleted
- **Fresh start**: Every reset/rerun starts with clean slate
- **No accumulation**: Prevents buildup of stale responses

### ✅ Consistent Workflow
- **Reset to Prestage**: Deletes all responses, batch ready for re-staging
- **Rerun Analysis**: Deletes all responses, recreates fresh ones
- **Both operations**: Include response counts in return data

### ✅ Robust Error Handling
- **Verification**: Confirms deletion actually worked
- **Retry logic**: Attempts second deletion if first fails
- **Comprehensive logging**: Tracks before/after counts

### ✅ External System Clarity
- **No stale data**: External system only sees current responses
- **Clear status**: All responses start with 'QUEUED' status
- **Proper batch_id**: All responses correctly linked to batch

## Current Status

**Both operations now properly clean up LLM responses:**

| Operation | Before Fix | After Fix |
|-----------|------------|-----------|
| **Reset to Prestage** | ❌ No cleanup | ✅ Deletes all responses |
| **Rerun Analysis** | ⚠️ Basic delete | ✅ Verified deletion + recreation |

**Database consistency maintained:**
- DocumentEvaluator: Tracks batch/document state
- KnowledgeDocuments: Clean LLM response state
- External system: Processes only current responses

The LLM response cleanup is now working correctly for both reset and rerun operations!