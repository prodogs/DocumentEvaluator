# BatchService Refactoring Plan: Centralized State Management

## Problem Statement
Currently, batch state management is fragmented:
- UI can directly call endpoints that change batch state
- No centralized validation of state transitions
- Race conditions between UI actions and background processing
- Batch integrity can be compromised by poorly-timed UI requests

## Solution: BatchService as Single Source of Truth

### Core Principles
1. **BatchService owns all state transitions**
2. **All batch modifications go through BatchService validation**
3. **UI requests are treated as "requests" not "commands"**
4. **BatchService enforces state machine integrity**
5. **Background processors report to BatchService, not directly to DB**

### Batch State Machine
```
SAVED -> STAGING -> STAGED -> ANALYZING -> COMPLETED
                      |          |            |
                      v          v            v
                   FAILED    PAUSED       FAILED
```

### Valid State Transitions
- SAVED -> STAGING (when staging starts)
- STAGING -> STAGED (when staging completes)
- STAGING -> FAILED (when staging fails)
- STAGED -> ANALYZING (when processing starts)
- ANALYZING -> COMPLETED (when all tasks finish)
- ANALYZING -> FAILED (when critical error)
- ANALYZING -> PAUSED (user request, if valid)
- PAUSED -> ANALYZING (resume processing)
- COMPLETED -> STAGING (restage for rerun)
- FAILED -> STAGING (retry after failure)

### Implementation Changes

#### 1. BatchService Methods
```python
class BatchService:
    def request_state_change(self, batch_id: int, requested_action: str, context: dict) -> dict:
        """
        Central method for all state change requests
        - Validates current state
        - Checks if transition is allowed
        - Performs transition if valid
        - Returns success/failure with reason
        """
        
    def can_transition(self, batch_id: int, to_action: str) -> tuple[bool, str]:
        """Check if a state transition is currently valid"""
        
    def handle_task_completion(self, task_id: str, result: dict) -> None:
        """Handle task completion from queue processor"""
        
    def handle_task_failure(self, task_id: str, error: dict) -> None:
        """Handle task failure from queue processor"""
```

#### 2. API Routes Changes
```python
# Before:
@app.route('/api/batches/<int:batch_id>/reset-to-prestage', methods=['POST'])
def reset_batch_to_prestage(batch_id):
    result = batch_service.reset_batch_to_prestage(batch_id)
    
# After:
@app.route('/api/batches/<int:batch_id>/action', methods=['POST'])
def batch_action(batch_id):
    action = request.json.get('action')  # 'reset', 'pause', 'resume', etc.
    context = request.json.get('context', {})
    result = batch_service.request_state_change(batch_id, action, context)
```

#### 3. State Validation Rules
- **Reset**: Only allowed if batch is in SAVED, FAILED, or COMPLETED state
- **Pause**: Only allowed if batch is ANALYZING and has active tasks
- **Resume**: Only allowed if batch is PAUSED
- **Cancel**: Only allowed if batch is ANALYZING or PAUSED
- **Restage**: Only allowed if batch is COMPLETED or FAILED

#### 4. Queue Processor Integration
```python
# Queue processor should report back to BatchService, not update DB directly
class BatchQueueProcessor:
    def process_task_completion(self, task_id, result):
        # Don't update llm_responses directly
        # Report to BatchService
        batch_service.handle_task_completion(task_id, result)
```

#### 5. Concurrency Protection
- Use database row locking when reading batch state
- Use optimistic locking with version numbers
- Queue state change requests if batch is locked

### Migration Steps
1. Add `request_state_change` method to BatchService
2. Create state validation logic
3. Update all API endpoints to use new method
4. Update queue processors to report to BatchService
5. Add database locking/versioning
6. Update UI to use new unified endpoint

### Benefits
- Single source of truth for batch state
- No race conditions
- Clear audit trail of state changes
- Easier to add new states/transitions
- Better error messages for invalid operations
- Simplified UI logic (just request, don't manage state)