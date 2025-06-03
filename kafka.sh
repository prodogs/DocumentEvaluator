#!/bin/bash

# Kafka Docker Launcher Script
# This script provides easy access to Kafka Docker tools from the project root

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KAFKA_DIR="$SCRIPT_DIR/kafka-docker"

# Check if kafka-docker directory exists
if [ ! -d "$KAFKA_DIR" ]; then
    echo "Error: kafka-docker directory not found at $KAFKA_DIR"
    exit 1
fi

# Check if the main kafka script exists
KAFKA_SCRIPT="$KAFKA_DIR/kafka-docker.sh"
if [ ! -f "$KAFKA_SCRIPT" ]; then
    echo "Error: kafka-docker.sh not found at $KAFKA_SCRIPT"
    exit 1
fi

# Make sure the script is executable
chmod +x "$KAFKA_SCRIPT"

# Forward all arguments to the kafka-docker.sh script
exec "$KAFKA_SCRIPT" "$@"
