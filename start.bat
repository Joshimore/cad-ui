@echo off
rem CAD UI — start script. Double-click to launch the system.
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
    echo [CAD UI] First run: creating virtual environment...
    python -m venv .venv
    if errorlevel 1 (
        echo.
        echo [CAD UI] ERROR: could not create venv.
        echo Install Python 3.11+ with pip and make sure "python" is on PATH.
        pause
        exit /b 1
    )
    echo [CAD UI] Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [CAD UI] ERROR: dependency install failed. See output above.
        echo If pip is missing, your Python build ships without it - install a standard Python 3.11+.
        pause
        exit /b 1
    )
)

echo [CAD UI] Starting... browser will open at http://127.0.0.1:8145
".venv\Scripts\python.exe" run_ui.py
if errorlevel 1 pause
