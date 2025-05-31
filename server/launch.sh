#!/bin/bash

echo "Starting Document Evaluator Service..."

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

# Launch the Flask application using the proper launcher
echo "Launching Flask application..."
python app_launcher.py

# Note: To run in the background, use:
# python app.py > app.log 2>&1 &
# echo $! > app.pid
