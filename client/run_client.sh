#!/bin/bash

# Client Runner Script for DocumentEvaluator
# This script manages the React client application

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Configuration
CLIENT_DIR="$(dirname "$0")"
PORT=5173
LOG_FILE="client.log"

# Function to check if port is in use
check_port() {
    if lsof -Pi :$PORT -sTCP:LISTEN -t >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Function to kill process on port
kill_port() {
    echo -e "${YELLOW}Checking for existing processes on port $PORT...${NC}"
    if check_port; then
        echo -e "${YELLOW}Found process on port $PORT. Killing it...${NC}"
        lsof -ti:$PORT | xargs kill -9 2>/dev/null
        sleep 2
        echo -e "${GREEN}Process killed successfully${NC}"
    else
        echo -e "${GREEN}No process found on port $PORT${NC}"
    fi
}

# Function to start client
start_client() {
    echo -e "${GREEN}Starting DocumentEvaluator Client...${NC}"
    echo "----------------------------------------"
    
    # Change to client directory
    cd "$CLIENT_DIR" || exit 1
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}node_modules not found. Running npm install...${NC}"
        npm install
        if [ $? -ne 0 ]; then
            echo -e "${RED}npm install failed. Please check your Node.js installation.${NC}"
            exit 1
        fi
    fi
    
    # Start the development server
    echo -e "${GREEN}Starting development server on port $PORT...${NC}"
    npm run dev
}

# Function to start client in background
start_background() {
    echo -e "${GREEN}Starting DocumentEvaluator Client in background...${NC}"
    echo "----------------------------------------"
    
    # Change to client directory
    cd "$CLIENT_DIR" || exit 1
    
    # Check if node_modules exists
    if [ ! -d "node_modules" ]; then
        echo -e "${YELLOW}node_modules not found. Running npm install...${NC}"
        npm install
        if [ $? -ne 0 ]; then
            echo -e "${RED}npm install failed. Please check your Node.js installation.${NC}"
            exit 1
        fi
    fi
    
    # Start in background with output to log file
    echo -e "${GREEN}Starting development server in background...${NC}"
    nohup npm run dev > "$LOG_FILE" 2>&1 &
    
    # Wait a moment for the server to start
    sleep 3
    
    # Check if it started successfully
    if check_port; then
        echo -e "${GREEN}✓ Client started successfully!${NC}"
        echo -e "${GREEN}  Access at: http://localhost:$PORT${NC}"
        echo -e "${YELLOW}  Logs: tail -f $CLIENT_DIR/$LOG_FILE${NC}"
        echo -e "${YELLOW}  Stop: $0 stop${NC}"
    else
        echo -e "${RED}✗ Failed to start client${NC}"
        echo -e "${RED}  Check logs: cat $CLIENT_DIR/$LOG_FILE${NC}"
        exit 1
    fi
}

# Function to show status
show_status() {
    if check_port; then
        echo -e "${GREEN}✓ Client is running on port $PORT${NC}"
        echo -e "  PID: $(lsof -ti:$PORT)"
        echo -e "  URL: http://localhost:$PORT"
    else
        echo -e "${YELLOW}✗ Client is not running${NC}"
    fi
}

# Function to show logs
show_logs() {
    if [ -f "$CLIENT_DIR/$LOG_FILE" ]; then
        tail -f "$CLIENT_DIR/$LOG_FILE"
    else
        echo -e "${YELLOW}No log file found${NC}"
    fi
}

# Main script logic
case "${1:-}" in
    "start")
        kill_port
        start_client
        ;;
    "background"|"bg")
        kill_port
        start_background
        ;;
    "stop")
        kill_port
        ;;
    "restart")
        kill_port
        start_client
        ;;
    "status")
        show_status
        ;;
    "logs")
        show_logs
        ;;
    *)
        echo "DocumentEvaluator Client Runner"
        echo "==============================="
        echo ""
        echo "Usage: $0 [command]"
        echo ""
        echo "Commands:"
        echo "  start       - Start client (kills existing process)"
        echo "  background  - Start client in background"
        echo "  bg          - Alias for background"
        echo "  stop        - Stop client"
        echo "  restart     - Restart client"
        echo "  status      - Show client status"
        echo "  logs        - Show client logs (when running in background)"
        echo ""
        echo "Default: start"
        echo ""
        # Default action
        kill_port
        start_client
        ;;
esac