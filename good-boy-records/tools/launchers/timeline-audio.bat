@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."

if exist ".venv-audio-analysis\Scripts\python.exe" (
  ".venv-audio-analysis\Scripts\python.exe" tools\timeline\audio.py %*
) else (
  py -3 tools\timeline\audio.py %*
)
set "RC=%ERRORLEVEL%"
goto :finish

:finish
echo.
if "%RC%"=="0" (
  echo Audio analysis finished successfully.
) else (
  echo ERROR: Audio analysis failed with exit code %RC%.
)
if not defined GBR_NO_PAUSE pause
exit /b %RC%
