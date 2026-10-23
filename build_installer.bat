@echo off
REM Makes installer\Output\dnd_ai_<version>_setup.exe: build the game, then wrap it with Inno Setup (free: https://jrsoftware.org/isinfo.php, version 6.1 or newer).
REM RAISE core\version.py BEFORE BUILDING. The game compares its own version with the newest release tag: an installer built from the old
REM number and attached to a new tag installs a game that thinks it is still old, and offers the same update forever.
for /f %%v in ('python -c "from core.version import VERSION; print(VERSION)"') do set DND_VERSION=%%v
echo Building version %DND_VERSION% (core\version.py). The release tag must be v%DND_VERSION%.
call build_exe.bat || goto :fail
set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" (
  echo Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php and run this again.
  pause
  exit /b 1
)
"%ISCC%" /DAppVersion=%DND_VERSION% installer\dnd_ai.iss || goto :fail
echo.
echo Built: installer\Output\dnd_ai_%DND_VERSION%_setup.exe
echo Attach it to a GitHub release tagged v%DND_VERSION% (the game finds it by the _setup.exe ending). Testers' games then offer the update.
pause
goto :eof
:fail
echo.
echo Build failed - see the messages above.
pause
exit /b 1
