#!/bin/bash

# Service keeper script for DocumentEvaluator server
# This script ensures the server keeps running and restarts if it crashes

SERVICE_NAME="DocumentEvaluator Server"
SERVICE_COMMAND="python app.py"
LOG_FILE="../service.log"
PID_FILE="server.pid"
CHECK_INTERVAL=10  # Check every 10 seconds

echo "Starting $SERVICE_NAME keeper..."
echo "Logs will be written to: $LOG_FILE"

# Function to check if service is running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p "$PID" > /dev/null 2>&1; then
            return 0
        fi
    fi
    return 1
}

# Function to start the service
start_service() {
    echo "[$(date)] Starting $SERVICE_NAME..."
    nohup $SERVICE_COMMAND >> "$LOG_FILE" 2>&1 &
    PID=$!
    echo $PID > "$PID_FILE"
    echo "[$(date)] $SERVICE_NAME started with PID: $PID"
}

# Function to stop the service
stop_service() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        echo "[$(date)] Stopping $SERVICE_NAME (PID: $PID)..."
        kill $PID 2>/dev/null
        rm -f "$PID_FILE"
    fi
}

# Handle SIGTERM and SIGINT
trap 'echo "[$(date)] Received shutdown signal, stopping..."; stop_service; exit 0' SIGTERM SIGINT

# Main loop
while true; do
    if ! is_running; then
        echo "[$(date)] $SERVICE_NAME is not running, restarting..."
        start_service
        sleep 5  # Give it time to start
    fi
    sleep $CHECK_INTERVAL
done