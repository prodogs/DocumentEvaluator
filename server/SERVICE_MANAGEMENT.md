# DocumentEvaluator Service Management

This document explains how to manage the DocumentEvaluator server service to ensure it runs continuously.

## Current Status

The server is currently running on port 5001. You can check its status at any time using:

```bash
./service_manager.sh status
```

## Service Manager Commands

The `service_manager.sh` script provides the following commands:

### Basic Operations

- **Start the service**: `./service_manager.sh start`
- **Stop the service**: `./service_manager.sh stop`
- **Restart the service**: `./service_manager.sh restart`
- **Check status**: `./service_manager.sh status`
- **View logs**: `./service_manager.sh logs`

### System Service Installation (Auto-start)

To install the service so it automatically starts when you log in:

```bash
./service_manager.sh install
```

To uninstall from system services:

```bash
./service_manager.sh uninstall
```

## Manual Service Control

If you prefer to run the service manually:

### Start in background:
```bash
nohup python app.py > ../service.log 2>&1 &
```

### Check if running:
```bash
ps aux | grep -E "Python.*app\.py" | grep -v grep
```

### Stop the service:
```bash
# Find the PID
ps aux | grep -E "Python.*app\.py" | grep -v grep

# Kill the process
kill <PID>
```

## Service Files

- **service_manager.sh**: Main service management script
- **keep_alive.sh**: Alternative script that monitors and restarts the service if it crashes
- **com.documentevaluator.server.plist**: macOS launchd configuration for auto-start
- **../service.log**: Service logs

## Monitoring

The service includes health monitoring accessible at:
- Health endpoint: http://localhost:5001/api/health
- Swagger UI: http://localhost:5001/api/docs

## Troubleshooting

### Service won't start
1. Check if port 5001 is already in use: `lsof -i :5001`
2. Check the logs: `tail -100 ../service.log`
3. Ensure PostgreSQL is running and accessible

### Service stops unexpectedly
1. Check the logs for errors: `./service_manager.sh logs`
2. Use the install command to set up auto-restart: `./service_manager.sh install`

### High CPU usage
The service runs batch processing tasks. High CPU usage during batch processing is normal.

## Architecture Notes

The service uses:
- Flask web framework
- PostgreSQL database (primary: doc_eval, secondary: KnowledgeDocuments)
- Batch queue processor for document analysis
- Health monitoring and auto-recovery features

## Important URLs

- API Base: http://localhost:5001
- Health Check: http://localhost:5001/api/health
- API Documentation: http://localhost:5001/api/docs
- Monitoring Dashboard: http://localhost:5001/static/monitor.html