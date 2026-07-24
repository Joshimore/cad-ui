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
)

rem Install deps until they succeed. The marker is written only after a clean
rem install, so a failed/interrupted first run retries instead of wedging.
if not exist ".venv\.deps-ok" (
    echo [CAD UI] Installing dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 (
        echo.
        echo [CAD UI] ERROR: dependency install failed. See output above.
        echo If pip is missing, your Python build ships without it - install a standard Python 3.11+.
        pause
        exit /b 1
    )
    echo ok> ".venv\.deps-ok"
)

echo [CAD UI] Starting... browser will open at http://127.0.0.1:8145
".venv\Scripts\python.exe" run_ui.py
if errorlevel 1 pause
