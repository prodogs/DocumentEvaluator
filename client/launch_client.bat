@echo off
echo Starting Document Evaluator Web Client...

REM Check if Node.js is installed
where node >nul 2>&1
if %ERRORLEVEL% neq 0 (
    echo Error: Node.js is not installed or not in the PATH.
    echo Please install Node.js from https://nodejs.org/
    exit /b 1
)

REM Check if package.json exists
if not exist package.json (
    echo Warning: package.json not found. Setting up a new React project...

    REM Initialize a new React project with Vite
    echo Creating a new React project with Vite...
    npx create-vite@latest . --template react

    REM Install dependencies
    echo Installing dependencies...
    npm install axios react-router-dom

    REM Create a basic .env file
    echo Creating .env file...
    echo VITE_API_URL=http://localhost:5001 > .env
)

REM Install dependencies if node_modules doesn't exist
if not exist node_modules (
    echo Installing dependencies...
    npm install
)

REM Set the backend URL environment variable if not already set
if not defined VITE_API_URL (
    set VITE_API_URL=http://localhost:5001
)

REM Start the development server
echo Starting development server...
npm run dev

REM If the npm run dev fails, provide troubleshooting info
if %ERRORLEVEL% neq 0 (
    echo.
    echo There was an error starting the development server.
    echo Try running the following commands manually:
    echo - npm install
    echo - npm run dev
    exit /b 1
)
