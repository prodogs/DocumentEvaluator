#!/bin/bash

echo "Starting Document Evaluator Web Client..."

# Check if Node.js is installed
if ! command -v node &> /dev/null; then
    echo "Error: Node.js is not installed."
    echo "Please install Node.js from https://nodejs.org/"
    exit 1
 fi

# Check if package.json exists
if [ ! -f "package.json" ]; then
    echo "Warning: package.json not found. Setting up a new React project..."

    # Initialize a new React project with Vite
    echo "Creating a new React project with Vite..."
    npx create-vite@latest . --template react --force

    # Install dependencies
    echo "Installing dependencies..."
    npm install axios react-router-dom

    # Create a basic .env file
    echo "Creating .env file..."
    echo "VITE_API_URL=http://localhost:5001" > .env
fi

# Make sure dependencies are installed
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Set the backend URL environment variable if not already set
if [ -z "$VITE_API_URL" ]; then
    export VITE_API_URL=http://localhost:5001
fi

# Start the development server
echo "Starting development server..."
npm run dev

# If the npm run dev fails, provide troubleshooting info
if [ $? -ne 0 ]; then
    echo ""
    echo "There was an error starting the development server."
    echo "Try running the following commands manually:"
    echo "- npm install"
    echo "- npm run dev"
    exit 1
fi
