# Batch Staging Flow Guide

## Batch States and Actions

### States
- **SAVED**: Initial state after creating/saving a batch
- **STAGING**: Batch is being prepared (documents being encoded)
- **STAGED**: Ready to process
- **ANALYZING**: Processing in progress
- **PAUSED**: Processing paused
- **COMPLETED**: All processing done
- **FAILED**: Processing failed
- **FAILED_STAGING**: Staging failed

### Actions Based on Current State

#### For SAVED Batch (newly created):
- **Action**: `stage`
- **Endpoint**: `POST /api/batches/{batch_id}/stage`
- **Purpose**: Initial staging of documents for processing

#### For COMPLETED or FAILED Batch (needs reprocessing):
- **Action**: `restage`
- **Endpoint**: `POST /api/batches/{batch_id}/reprocess-staging`
- **Purpose**: Clear previous results and prepare for new processing run

#### For STAGED Batch:
- **Action**: `run`
- **Endpoint**: `POST /api/batches/{batch_id}/run`
- **Purpose**: Start processing documents

## API Endpoints Summary

### Creating and Staging
1. **Save Only**: `POST /api/batches/save` - Creates batch in SAVED state
2. **Stage Saved Batch**: `POST /api/batches/{batch_id}/stage` - Stages a SAVED batch
3. **Save & Stage**: `POST /api/batches/stage` - Creates and immediately stages

### Reprocessing
1. **Restage**: `POST /api/batches/{batch_id}/reprocess-staging` - For COMPLETED/FAILED batches
2. **Rerun**: `POST /api/batches/{batch_id}/rerun` - Complete rerun with new staging

### State Management
1. **Unified Action**: `POST /api/batches/{batch_id}/action`
   - Body: `{ "action": "stage|run|pause|resume|reset|cancel|restage" }`
   - Validates state transitions automatically

## Frontend Implementation Note

The UI should check the batch status and call the appropriate endpoint:
- If `status === 'SAVED'` → Use `/api/batches/{batch_id}/stage`
- If `status === 'COMPLETED' || status === 'FAILED'` → Use `/api/batches/{batch_id}/reprocess-staging`
- If `status === 'STAGED'` → Use `/api/batches/{batch_id}/run`

## Example Flow

```javascript
// For a newly saved batch
if (batch.status === 'SAVED') {
    // Stage it
    await fetch(`/api/batches/${batch.id}/stage`, { method: 'POST' });
}

// For a completed batch that needs reprocessing
if (batch.status === 'COMPLETED') {
    // Restage it
    await fetch(`/api/batches/${batch.id}/reprocess-staging`, { method: 'POST' });
}

// Using the unified action endpoint
await fetch(`/api/batches/${batch.id}/action`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ 
        action: batch.status === 'SAVED' ? 'stage' : 'restage' 
    })
});
```