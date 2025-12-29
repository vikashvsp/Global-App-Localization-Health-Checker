@echo off
echo Starting Global App Localization Health Checker...

:: Check if venv exists
if not exist ".venv" (
    echo Virtual environment not found. Setting up...
    python -m venv .venv
    call .venv\Scripts\activate
    echo Installing dependencies...
    pip install -r requirements.txt
    echo Installing Playwright browsers...
    playwright install
) else (
    call .venv\Scripts\activate
)

:: Run the Actor
echo Running Actor...
python -m src.main

pause
