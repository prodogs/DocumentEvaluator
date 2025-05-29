#!/bin/bash

echo "Starting Document Evaluator Service..."

# Function to kill Python processes related to the app
kill_python_app_processes() {
    echo "Checking for running Python app processes..."
    local PIDS=$(pgrep -f "python.*app_launcher.py")
    if [ -z "$PIDS" ]; then
        echo "No Python app processes found."
        return 0
    fi

    echo "Found Python app processes (PIDs: $PIDS). Attempting to terminate..."
    kill $PIDS 2>/dev/null || true
    sleep 2

    if pgrep -f "python.*app_launcher.py" >/dev/null; then
        echo "Processes still running. Attempting force kill..."
        kill -9 $PIDS 2>/dev/null || true
        sleep 1
        if pgrep -f "python.*app_launcher.py" >/dev/null; then
            echo "WARNING: Failed to kill all Python app processes."
            return 1
        fi
    fi
    echo "Python app processes terminated."
    return 0
}

# Function to kill process on port
kill_process_on_port() {
    local PORT=$1
    local PID

    echo "Checking for processes on port $PORT..."

    # Try multiple methods to find the PID
    if command -v lsof >/dev/null 2>&1; then
        PID=$(lsof -ti:$PORT)
    elif command -v ss >/dev/null 2>&1; then
        PID=$(ss -lptn "sport = :$PORT" | grep -oP '(?<=pid=)\d+')
    elif command -v netstat >/dev/null 2>&1; then
        if [ "$(uname)" == "Darwin" ]; then  # macOS
            PID=$(netstat -anv | grep "\.$PORT " | awk '{print $9}')
        else  # Linux
            PID=$(netstat -tnlp 2>/dev/null | grep ":$PORT " | awk '{print $7}' | cut -d'/' -f1)
        fi
    elif command -v fuser >/dev/null 2>&1; then
        PID=$(fuser $PORT/tcp 2>/dev/null)
    fi

    if [ -z "$PID" ]; then
        echo "No process found running on port $PORT."
        return 0
    fi

    echo "Found process (PID: $PID) running on port $PORT. Attempting to terminate..."

    # Try graceful kill first
    kill $PID 2>/dev/null || true
    sleep 2

    # Check if process is still running
    if ps -p $PID >/dev/null 2>&1; then
        echo "Process still running. Attempting force kill..."
        kill -9 $PID 2>/dev/null || true
        sleep 1

        # Final check
        if ps -p $PID >/dev/null 2>&1; then
            echo "WARNING: Failed to kill process on port $PORT."
            return 1
        fi
    fi

    echo "Port $PORT is now available."
    return 0
}

# Kill any existing Python app processes
kill_python_app_processes

# Kill any process running on port 5001
kill_process_on_port 5001

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if required packages are installed
echo "Checking dependencies..."
if [ -f "requirements.txt" ]; then
    pip install -r requirements.txt
fi



# Create openapi.json if it doesn't exist
if [ ! -f "openapi.json" ] && [ ! -f "static/swagger.json" ]; then
    echo "Warning: Neither openapi.json nor static/swagger.json found. Creating default openapi.json..."

    # Create static directory if it doesn't exist
    mkdir -p static

    # Create the default openapi.json file if it doesn't exist
    # We'll generate it or have a template in the future
    cp -f openapi.json static/swagger.json 2>/dev/null || echo "Note: No default openapi.json to copy"
fi

# Set environment variables for OpenAPI integration
export FLASK_APP=app.py
export OPENAPI_SPEC_PATH="./openapi.json"

# Install flask-swagger-ui if not already installed
pip install flask-swagger-ui

# Create static directory if it doesn't exist
mkdir -p static

# Ensure openapi.json has read permissions before copying
chmod +r openapi.json

# Copy openapi.json to the correct location for Swagger UI
# cp openapi.json static/swagger.json

# Launch the Flask application with OpenAPI support
echo "Launching Flask application with OpenAPI integration..."
export PYTHONPATH=$(pwd)/..
python -m server.app_launcher

# Note: To run in the background, use:
# python app.py > app.log 2>&1 &
# echo $! > app.pid
