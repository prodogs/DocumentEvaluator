#!/bin/bash

echo "Running backend tests..."

# Activate virtual environment if it exists
if [ -d "venv" ]; then
    echo "Activating virtual environment..."
    source venv/bin/activate
fi

# Check if test_backend.py exists
if [ ! -f "test_backend.py" ]; then
    echo "Error: test_backend.py not found in the current directory."
    exit 1
fi

# Ensure required packages are installed
echo "Checking if required packages are installed..."
pip install -q python-dotenv requests

# Run the test script
echo "Starting test execution..."
python test_backend.py

# Capture exit code
EXIT_CODE=$?

# Print result based on exit code
if [ $EXIT_CODE -eq 0 ]; then
    echo "Tests completed successfully."
else
    echo "Tests failed with exit code: $EXIT_CODE"
fi

exit $EXIT_CODE
