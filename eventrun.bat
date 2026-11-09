@echo off
setlocal
cd /d "%~dp0"
title Meravia - event run

where python >nul 2>nul
if errorlevel 1 (
    echo Python was not found. Install Python 3.10 or newer from python.org
    echo and tick "Add Python to PATH" during setup, then run play.bat again.
    pause
    exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
    echo First run: creating a private Python environment...
    python -m venv .venv
    if errorlevel 1 goto fail
)

if not exist ".venv\installed.flag" (
    echo First run: installing the game's libraries...
    ".venv\Scripts\python.exe" -m pip install --upgrade pip
    ".venv\Scripts\python.exe" -m pip install -r requirements.txt
    if errorlevel 1 goto fail
    echo done> ".venv\installed.flag"
)

REM (f531) The game runs its own model server: its builds under runtime\ and the model files under models\, each checked against
REM data\runtime\server.yaml. Whatever is missing is fetched once (the model files are about 8 GB).
".venv\Scripts\python.exe" -c "import sys; sys.path.insert(0, '.'); from llm import runtime; bad = runtime.runtime_problems(check_files=True); print('\n'.join(bad)); sys.exit(1 if bad else 0)" >nul 2>nul
if errorlevel 1 (
    echo The model server's files are not all here yet. Fetching them once...
    ".venv\Scripts\python.exe" tools\fetch_runtime.py --models
    if errorlevel 1 goto fail
    ".venv\Scripts\python.exe" tools\fetch_runtime.py --build cuda
    if errorlevel 1 goto fail
    ".venv\Scripts\python.exe" tools\fetch_runtime.py --build vulkan
    if errorlevel 1 goto fail
    ".venv\Scripts\python.exe" tools\fetch_runtime.py --build cpu
    if errorlevel 1 goto fail
)

".venv\Scripts\python.exe" tools\eventrun.py %*
echo.
pause
exit /b 0

:fail
echo.
echo Setup failed. See the messages above.
pause
exit /b 1
