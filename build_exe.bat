@echo off
REM Builds dist\Meravia\Meravia.exe, the windowed game (run from the project folder:  build_exe.bat)
REM Needs Python 3.11+ on PATH. Ollama and the model are NOT bundled: the game checks for them on first launch and offers to install them.
REM To make a setup.exe for testers, run build_installer.bat instead (it calls this first).
python -m venv .buildenv || goto :fail
call .buildenv\Scripts\activate.bat || goto :fail
python -m pip install --upgrade pip || goto :fail
python -m pip install -r requirements.txt pyinstaller || goto :fail
python -m PyInstaller --noconfirm --clean --onedir --noconsole --name Meravia ^
  --add-data "data;data" --add-data "ui\gui\web;ui\gui\web" --add-data "CREDITS.md;." ^
  --collect-submodules core --collect-submodules engine --collect-submodules character --collect-submodules llm ^
  --collect-submodules npc --collect-submodules scenes --collect-submodules storage --collect-submodules ui --collect-submodules world ^
  --collect-all pydantic --collect-all pydantic_core --collect-all ollama --collect-all webview ^
  main.py || goto :fail
echo.
echo Built: dist\Meravia\Meravia.exe  (opens the game window; run it with --terminal for the text version)
echo Saves and logs are created next to the exe (dist\Meravia\saves, dist\Meravia\logs).
echo On first launch the game checks for Ollama and the model and offers to install and download them.
goto :eof
:fail
echo Build failed.
exit /b 1
