@echo off
setlocal
cd /d "%~dp0"
title Meravia - night run

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

where ollama >nul 2>nul
if errorlevel 1 (
    echo Ollama was not found. Install it from ollama.com, then run play.bat again.
    pause
    exit /b 1
)

ollama list >nul 2>nul
if errorlevel 1 (
    echo Ollama is not running. Start the Ollama app, wait a few seconds, then run play.bat again.
    pause
    exit /b 1
)

for /f "tokens=2 delims== " %%M in ('findstr /b "MODEL" config.py') do set MODEL=%%~M
ollama list | findstr /i /c:"%MODEL%" >nul
if errorlevel 1 (
    echo Downloading the model %MODEL% - this is a large one-time download...
    ollama pull %MODEL%
    if errorlevel 1 goto fail
)

".venv\Scripts\python.exe" tools\nightrun.py %*
echo.
pause
exit /b 0

:fail
echo.
echo Setup failed. See the messages above.
pause
exit /b 1
