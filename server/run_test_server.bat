@echo off
echo Testing Document Evaluator Service endpoints...

REM Activate virtual environment if it exists
if exist venv\Scripts\activate.bat (
    echo Activating virtual environment...
    call venv\Scripts\activate.bat
)

REM Run the test script
python test_server.py

echo Test complete.
pause
