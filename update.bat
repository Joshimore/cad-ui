@echo off
rem CAD UI — auto-update script: pulls the latest version from the repository.
cd /d "%~dp0"

echo [CAD UI] Updating from repository...
git pull --ff-only
if errorlevel 1 (
    echo.
    echo [CAD UI] ERROR: update failed.
    echo Possible reasons: no remote configured, no network, or local changes conflict.
    echo Check "git status" / "git remote -v" and try again.
    pause
    exit /b 1
)

if exist ".venv\Scripts\python.exe" (
    echo [CAD UI] Syncing dependencies...
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt -q
    if errorlevel 1 (
        echo.
        echo [CAD UI] ERROR: dependency sync failed. See output above.
        echo The code is updated but dependencies are stale - fix the error, then rerun update.bat.
        if exist ".venv\.deps-ok" del ".venv\.deps-ok"
        pause
        exit /b 1
    )
    echo ok> ".venv\.deps-ok"
)

echo.
echo [CAD UI] Updated. Restart CAD UI (start.bat) to apply.
pause
