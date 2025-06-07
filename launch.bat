@echo off
REM --- launch.bat ---
REM This script activates the Python virtual environment and runs main.py

REM Define the path to your project directory.
REM IMPORTANT: Make sure this path is correct for your system.
set "PROJECT_DIR=C:\Users\admin\StreamingSimplifier"

REM Navigate to the project directory
cd /d "%PROJECT_DIR%"

REM Activate the virtual environment
REM This will run the 'activate.bat' script inside your .venv
call ".\.venv\Scripts\activate.bat"

REM Check if the virtual environment activation was successful (optional but good practice)
if not exist ".\.venv\Scripts\python.exe" (
    echo Error: Virtual environment not found or not activated.
    pause
    exit /b 1
)

REM Run your main Python application
echo Launching main.py...
python main.py

REM Optional: Keep the command window open after the script finishes.
REM Remove 'pause' if you want the window to close immediately after main.py exits,
REM especially when using AHK's 'Hide' option.

REM Exit the batch script
exit /b 0