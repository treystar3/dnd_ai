@echo off
REM Builds dist\dnd_ai\dnd_ai.exe, the windowed game (run from the project folder:  build_exe.bat)
REM Needs Python 3.11+ on PATH. Ollama and the model are NOT bundled: the game checks for them on first launch and offers to install them.
REM To make a setup.exe for testers, run build_installer.bat instead (it calls this first).
python -m venv .buildenv || goto :fail
call .buildenv\Scripts\activate.bat || goto :fail
python -m pip install --upgrade pip || goto :fail
python -m pip install -r requirements.txt pyinstaller || goto :fail
python -m PyInstaller --noconfirm --clean --onedir --noconsole --name dnd_ai ^
  --add-data "data;data" --add-data "ui\gui\web;ui\gui\web" ^
  --collect-submodules core --collect-submodules engine --collect-submodules character --collect-submodules llm ^
  --collect-submodules npc --collect-submodules scenes --collect-submodules storage --collect-submodules ui --collect-submodules world ^
  --collect-all pydantic --collect-all pydantic_core --collect-all ollama --collect-all webview ^
  main.py || goto :fail
echo.
echo Built: dist\dnd_ai\dnd_ai.exe  (opens the game window; run it with --terminal for the text version)
echo Saves and logs are created next to the exe (dist\dnd_ai\saves, dist\dnd_ai\logs).
echo On first launch the game checks for Ollama and the model and offers to install and download them.
goto :eof
:fail
echo Build failed.
exit /b 1
