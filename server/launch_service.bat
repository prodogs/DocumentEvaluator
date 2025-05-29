@echo off
echo Starting Document Evaluator Service...

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Check if required packages are installed
echo Checking dependencies...
if exist requirements.txt (
    pip install -r requirements.txt
)

REM Check if openapi.json exists
if not exist openapi.json (
    if not exist static\swagger.json (
        echo Warning: Neither openapi.json nor static\swagger.json found. Will look for it in OPENAPI_SPEC_PATH.
    )
    REM We'll let app_launcher.py handle this, as it has fallback mechanisms
)

REM Set environment variables for OpenAPI integration
set FLASK_APP=app.py
set OPENAPI_SPEC_PATH=.\openapi.json

REM Install flask-swagger-ui if not already installed
pip install flask-swagger-ui

REM Create static directory if it doesn't exist
if not exist static mkdir static

REM Copy openapi.json to the correct location for Swagger UI if it exists
if exist openapi.json (
    copy openapi.json static\swagger.json
) else (
    echo Warning: openapi.json not found. Swagger UI may not work correctly.
)

REM Set custom port
set PORT=5001

REM Launch the Flask application with OpenAPI support
echo Launching Flask application with OpenAPI integration...
python app_launcher.py

REM Note: To run in the background on Windows, you can use:
REM start /B python app.py > app.log 2>&1
