@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "RC=0"

if not exist ".venv-audio-analysis\Scripts\python.exe" (
  echo Creating audio-analysis environment...
  py -3 -m venv .venv-audio-analysis
  if errorlevel 1 (
    set "RC=%ERRORLEVEL%"
    goto :finish
  )
)

".venv-audio-analysis\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 (
  set "RC=%ERRORLEVEL%"
  goto :finish
)

".venv-audio-analysis\Scripts\python.exe" -m pip install -r tools\timeline\requirements-audio.txt
if errorlevel 1 (
  set "RC=%ERRORLEVEL%"
  goto :finish
)

echo Audio/dance environment ready.

:finish
echo.
if not "%RC%"=="0" echo ERROR: Audio environment setup failed with exit code %RC%.
if not defined GBR_NO_PAUSE pause
exit /b %RC%
