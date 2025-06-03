# Startup Recovery Implementation

## Overview

This document describes the startup recovery functionality implemented to handle stuck batches and documents when the DocumentEvaluator service restarts after an unexpected shutdown or crash.

## Problem Statement

Previously, when the service was restarted:
- Batches in `ANALYZING` or `STAGING` status would remain stuck
- Documents in `PROCESSING` status would not be recovered
- Manual intervention was required to reset these entities

## Solution

A new `StartupRecoveryService` has been implemented that automatically:
1. Detects and recovers stuck batches
2. Resets stuck documents
3. Identifies orphaned tasks for monitoring
4. Provides detailed logging of recovery actions

## Implementation Details

### Files Added/Modified

1. **`server/services/startup_recovery.py`** (NEW)
   - Core recovery service implementation
   - Handles batch, document, and task recovery
   - Provides recovery summary and statistics

2. **`server/app.py`** (MODIFIED)
   - Added startup recovery to `initialize_services()`
   - Recovery runs before other services start

3. **`server/api/maintenance_routes.py`** (MODIFIED)
   - Added recovery status endpoint: `GET /api/maintenance/recovery/status`
   - Added manual recovery trigger: `POST /api/maintenance/recovery/run`
   - Added recovery task monitoring: `GET /api/maintenance/recovery/task/<task_id>`

### Recovery Logic

#### Batch Recovery
- Detects batches stuck in `ANALYZING` or `STAGING` status
- For `STAGING` batches: Reset to `SAVED` status
- For `ANALYZING` batches:
  - If all documents completed: Mark batch as `COMPLETED`
  - Otherwise: Reset to `STAGED` for re-processing

#### Document Recovery
- Finds documents in `PROCESSING` status without active tasks
- Resets them to `QUEUED` status
- Clears task_id and processing timestamps

#### Task Recovery
- Identifies documents with task_ids that need monitoring
- These are picked up by the batch_queue_processor's existing recovery logic

## Usage

### Automatic Recovery
Recovery runs automatically when the service starts:
```bash
python app.py
```

Look for recovery logs in the startup output:
```
============================================================
PERFORMING STARTUP RECOVERY
============================================================
Starting recovery process for stuck batches and documents
...
Recovery completed in X.XX seconds
Batches recovered: N
Documents recovered: N
Tasks recovered: N
============================================================
```

### Manual Recovery
You can trigger recovery manually via the API:

```bash
# Check last recovery status
curl http://localhost:5001/api/maintenance/recovery/status

# Trigger manual recovery
curl -X POST http://localhost:5001/api/maintenance/recovery/run

# Monitor recovery task
curl http://localhost:5001/api/maintenance/recovery/task/<task_id>
```

### Testing

Test scripts are provided:

1. **Create stuck batches for testing:**
   ```bash
   python create_stuck_batch_for_testing.py
   python create_stuck_batch_for_testing.py --staging
   ```

2. **Test recovery functionality:**
   ```bash
   python test_recovery.py
   ```

## Recovery Scenarios

### Scenario 1: Service Crash During Batch Processing
- Batch status: `ANALYZING`
- Recovery action: Check document completion
  - If all complete → `COMPLETED`
  - If incomplete → `STAGED`

### Scenario 2: Service Crash During Staging
- Batch status: `STAGING`
- Recovery action: Reset to `SAVED`

### Scenario 3: Documents Stuck Processing
- Document status: `PROCESSING` with no/old task_id
- Recovery action: Reset to `QUEUED`

### Scenario 4: Active Tasks
- Document status: `PROCESSING` with valid task_id
- Recovery action: Log for monitoring by batch_queue_processor

## Benefits

1. **Automatic Recovery**: No manual intervention required
2. **Clean State**: System starts with clean processing states
3. **Audit Trail**: Detailed logging of all recovery actions
4. **API Access**: Can trigger and monitor recovery via API
5. **Graceful Handling**: Preserves completed work while resetting stuck items

## Future Enhancements

1. Add metrics/monitoring for recovery frequency
2. Implement configurable recovery policies
3. Add webhook notifications for recovery events
4. Create UI component for recovery management