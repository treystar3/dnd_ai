@echo off
REM Makes installer\Output\Meravia_<version>_setup.exe: build the game, then wrap it with Inno Setup (free: https://jrsoftware.org/isinfo.php, version 6.1 or newer).
REM RAISE core\version.py BEFORE BUILDING. The game compares its own version with the newest release tag: an installer built from the old
REM number and attached to a new tag installs a game that thinks it is still old, and offers the same update forever.
for /f %%v in ('python -c "from core.version import VERSION; print(VERSION)"') do set GAME_VERSION=%%v
echo Building version %GAME_VERSION% (core\version.py). The release tag must be v%GAME_VERSION%.
call build_exe.bat || goto :fail
set ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" set ISCC=%LOCALAPPDATA%\Programs\Inno Setup 6\ISCC.exe
if not exist "%ISCC%" (
  echo Inno Setup 6 was not found. Install it from https://jrsoftware.org/isdl.php and run this again.
  pause
  exit /b 1
)
"%ISCC%" /DAppVersion=%GAME_VERSION% installer\meravia.iss || goto :fail
echo.
echo Built: installer\Output\Meravia_%GAME_VERSION%_setup.exe
echo Attach it to a GitHub release tagged v%GAME_VERSION% (the game finds it by the _setup.exe ending). Testers' games then offer the update.
pause
goto :eof
:fail
echo.
echo Build failed - see the messages above.
pause
exit /b 1
