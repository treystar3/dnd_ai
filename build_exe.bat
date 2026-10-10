@echo off
REM Builds dist\dnd_ai\dnd_ai.exe  (run from the project folder:  build_exe.bat)
REM Needs Python 3.11+ on PATH. Ollama and the model are NOT bundled - see the note at the end.
python -m venv .buildenv || goto :fail
call .buildenv\Scripts\activate.bat || goto :fail
python -m pip install --upgrade pip || goto :fail
python -m pip install -r requirements.txt pyinstaller || goto :fail
python -m PyInstaller --noconfirm --clean --onedir --name dnd_ai ^
  --add-data "data;data" ^
  --collect-submodules core --collect-submodules engine --collect-submodules character --collect-submodules llm ^
  --collect-submodules npc --collect-submodules scenes --collect-submodules storage --collect-submodules ui --collect-submodules world ^
  --collect-all pydantic --collect-all pydantic_core --collect-all ollama ^
  main.py || goto :fail
echo.
echo Built: dist\dnd_ai\dnd_ai.exe
echo Saves and logs are created next to the exe (dist\dnd_ai\saves, dist\dnd_ai\logs).
echo Players need Ollama installed and the model pulled once:  ollama pull gemma4:12b
goto :eof
:fail
echo Build failed.
exit /b 1
