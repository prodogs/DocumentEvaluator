#!/bin/bash

# DocumentEvaluator Service Manager
# This script helps manage the DocumentEvaluator server

SERVICE_NAME="DocumentEvaluator Server"
PLIST_FILE="com.documentevaluator.server.plist"
LAUNCHD_PATH="$HOME/Library/LaunchAgents/$PLIST_FILE"
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"

function show_help() {
    echo "DocumentEvaluator Service Manager"
    echo "Usage: $0 {start|stop|restart|status|install|uninstall|logs}"
    echo ""
    echo "Commands:"
    echo "  start     - Start the service"
    echo "  stop      - Stop the service"
    echo "  restart   - Restart the service"
    echo "  status    - Show service status"
    echo "  install   - Install as a system service (auto-start on login)"
    echo "  uninstall - Remove from system services"
    echo "  logs      - Show recent logs"
}

function check_status() {
    if pgrep -f "Python.*app\.py" > /dev/null; then
        echo "✅ $SERVICE_NAME is running"
        echo "PID: $(pgrep -f "Python.*app\.py")"
        return 0
    else
        echo "❌ $SERVICE_NAME is not running"
        return 1
    fi
}

function start_service() {
    echo "Starting $SERVICE_NAME..."
    
    if check_status > /dev/null 2>&1; then
        echo "Service is already running"
        return 0
    fi
    
    cd "$SCRIPT_DIR"
    nohup python app.py > ../service.log 2>&1 &
    
    sleep 2
    if check_status > /dev/null 2>&1; then
        echo "✅ Service started successfully"
    else
        echo "❌ Failed to start service"
        return 1
    fi
}

function stop_service() {
    echo "Stopping $SERVICE_NAME..."
    
    PID=$(pgrep -f "Python.*app\.py")
    if [ -z "$PID" ]; then
        echo "Service is not running"
        return 0
    fi
    
    kill -TERM $PID
    sleep 2
    
    if pgrep -f "Python.*app\.py" > /dev/null; then
        echo "Force stopping..."
        kill -9 $PID
    fi
    
    echo "✅ Service stopped"
}

function restart_service() {
    stop_service
    sleep 1
    start_service
}

function install_service() {
    echo "Installing $SERVICE_NAME as system service..."
    
    # Copy plist to LaunchAgents
    cp "$SCRIPT_DIR/$PLIST_FILE" "$LAUNCHD_PATH"
    
    # Load the service
    launchctl load "$LAUNCHD_PATH"
    
    echo "✅ Service installed and started"
    echo "The service will now start automatically on login"
}

function uninstall_service() {
    echo "Uninstalling $SERVICE_NAME from system services..."
    
    # Unload the service
    if [ -f "$LAUNCHD_PATH" ]; then
        launchctl unload "$LAUNCHD_PATH"
        rm "$LAUNCHD_PATH"
        echo "✅ Service uninstalled"
    else
        echo "Service is not installed"
    fi
}

function show_logs() {
    echo "Recent logs from $SERVICE_NAME:"
    echo "================================"
    tail -50 ../service.log
}

# Main script logic
case "$1" in
    start)
        start_service
        ;;
    stop)
        stop_service
        ;;
    restart)
        restart_service
        ;;
    status)
        check_status
        ;;
    install)
        install_service
        ;;
    uninstall)
        uninstall_service
        ;;
    logs)
        show_logs
        ;;
    *)
        show_help
        exit 1
        ;;
esac

exit 0