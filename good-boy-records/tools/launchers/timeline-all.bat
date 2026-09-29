@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "GBR_NO_PAUSE=1"
set "RC=0"

echo ========================================
echo GBR FULL TIMELINE BUILD
echo ========================================
echo.

echo [1/3] Lyrics...
call tools\launchers\timeline-lyrics.bat %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" goto :finish

echo.
echo [2/3] Audio / dance analysis...
call tools\launchers\timeline-audio.bat %*
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" goto :finish

echo.
echo [3/3] Playback merge...
call tools\launchers\timeline-playback.bat %*
set "RC=%ERRORLEVEL%"

:finish
set "GBR_NO_PAUSE="
echo.
echo ========================================
if "%RC%"=="0" (
  echo GBR FULL TIMELINE BUILD COMPLETE
) else (
  echo GBR FULL TIMELINE BUILD FAILED - EXIT %RC%
)
echo ========================================
pause
exit /b %RC%
