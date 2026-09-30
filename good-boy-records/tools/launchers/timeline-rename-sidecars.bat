@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."

set "RC=0"
py -3 tools\timeline\rename_sidecars.py %*
set "RC=%ERRORLEVEL%"

echo.
if "%RC%"=="0" (
  echo Sidecar rename finished successfully.
) else (
  echo ERROR: Sidecar rename finished with exit code %RC%.
)
if not defined GBR_NO_PAUSE pause
exit /b %RC%
