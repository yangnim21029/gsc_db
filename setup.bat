@echo off
REM GSC Database Manager - Windows Setup Script
REM Alternative to Just for Windows users

echo ================================================
echo GSC Database Manager - Windows Setup
echo ================================================

REM Check if Python is installed
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ERROR: Python is not installed or not in PATH
    echo Please install Python 3.11+ from https://python.org/downloads/
    echo Make sure to check "Add Python to PATH" during installation
    pause
    exit /b 1
)

REM Check if Poetry is installed
poetry --version >nul 2>&1
if %errorlevel% neq 0 (
    echo Installing Poetry...
    pip install poetry
    if %errorlevel% neq 0 (
        echo ERROR: Failed to install Poetry
        pause
        exit /b 1
    )
)

REM Run setup script
echo Running project initialization...
python setup.py

REM Install dependencies
echo Installing project dependencies...
poetry install

echo.
echo ================================================
echo Setup completed successfully!
echo ================================================
echo.
echo Next steps:
echo 1. Set up Google API credentials in cred\ directory
echo 2. Run: poetry run gsc-cli auth login
echo 3. Add your first site: poetry run gsc-cli site add "sc-domain:example.com"
echo.
echo For detailed instructions, see README.md
echo.
pause
