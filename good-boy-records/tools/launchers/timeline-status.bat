@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
py -3 tools\timeline\status.py %*
set "RC=%ERRORLEVEL%"
echo.
if not defined GBR_NO_PAUSE pause
exit /b %RC%
