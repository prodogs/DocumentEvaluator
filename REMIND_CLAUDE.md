# Quick Reminder for Claude

## What We're Doing
Implementing stability improvements to prevent cascading failures in DocumentEvaluator.

## Current Task
We just added monitoring endpoints. User needs to:
1. Restart the server
2. Test monitoring endpoints
3. Report back any issues

## Next Session Prompts
Just say one of these:
- "Let's continue with stability improvements"
- "Continue from STABILITY_PROGRESS.md"
- "What's next for stability?"

## Key Files
- `/STABILITY_PROGRESS.md` - Our progress tracker
- `/server/utils/stability_helpers.py` - Retry, circuit breaker, etc.
- `/server/api/monitoring_routes.py` - Monitoring endpoints
- `/TEST_RESULTS_SUMMARY.md` - Previous test results

## The Problem We're Solving
"how does this happen you fix one thing and break another" - Using proper patterns to prevent this.