@echo off
REM Builds dist\Meravia\Meravia.exe, the windowed game (run from the project folder:  build_exe.bat)
REM Needs Python 3.11+ on PATH. (f531) The game ships its own model server: the llama-server builds under runtime\<build>\ are copied
REM beside the exe (the CUDA and Vulkan builds and the processor's; fetch them first: python tools\fetch_runtime.py --build cuda
REM --platform windows, then --build vulkan, --build cpu). The model files (models\*.gguf) are NEVER in the build: on Steam they are a
REM depot of their own, and the testers' installer downloads them by their checksums (build_installer.bat, tools\installer_files.py).
REM To make a setup.exe for testers, run build_installer.bat instead (it calls this first).
python -m venv .buildenv || goto :fail
call .buildenv\Scripts\activate.bat || goto :fail
python -m pip install --upgrade pip || goto :fail
python -m pip install -r requirements.txt pyinstaller || goto :fail
python -m PyInstaller --noconfirm --clean --onedir --noconsole --name Meravia ^
  --add-data "data;data" --add-data "ui\gui\web;ui\gui\web" --add-data "CREDITS.md;." ^
  --collect-submodules core --collect-submodules engine --collect-submodules character --collect-submodules llm ^
  --collect-submodules npc --collect-submodules scenes --collect-submodules storage --collect-submodules ui --collect-submodules world ^
  --collect-all pydantic --collect-all pydantic_core --collect-all webview ^
  main.py || goto :fail
if exist "runtime\cuda\llama-server.exe"   xcopy /E /I /Y /Q "runtime\cuda"   "dist\Meravia\runtime\cuda"   >nul
if exist "runtime\vulkan\llama-server.exe" xcopy /E /I /Y /Q "runtime\vulkan" "dist\Meravia\runtime\vulkan" >nul
if exist "runtime\cpu\llama-server.exe"    xcopy /E /I /Y /Q "runtime\cpu"    "dist\Meravia\runtime\cpu"    >nul
if not exist "dist\Meravia\runtime" (
  echo No server build was found under runtime\. Fetch one first:  python tools\fetch_runtime.py --build cuda --platform windows
  goto :fail
)
echo.
echo Built: dist\Meravia\Meravia.exe  (opens the game window; run it with --terminal for the text version)
echo Saves and logs are created next to the exe (dist\Meravia\saves, dist\Meravia\logs); the server's builds are in dist\Meravia\runtime.
echo The model files are not in the build: the installer fetches them, or put them beside the exe yourself (python tools\fetch_runtime.py --models).
goto :eof
:fail
echo Build failed.
exit /b 1
