@echo off
REM Makes installer\Output\dnd_ai_setup.exe: build the game, then wrap it with Inno Setup (free: https://jrsoftware.org/isinfo.php, version 6.1 or newer).
call build_exe.bat || goto :fail
set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" (
  echo Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php and run this again.
  pause
  exit /b 1
)
for /f %%v in ('python -c "from core.version import VERSION; print(VERSION)"') do set DND_VERSION=%%v
"%ISCC%" /DAppVersion=%DND_VERSION% installer\dnd_ai.iss || goto :fail
echo.
echo Built: installer\Output\dnd_ai_setup.exe - send that file to your testers.
pause
goto :eof
:fail
echo.
echo Build failed - see the messages above.
pause
exit /b 1
