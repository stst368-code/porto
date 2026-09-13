@echo off
setlocal
cd /d "%~dp0"

call BUILD-SHOWCASE.bat
if errorlevel 1 exit /b 1

where py >nul 2>nul
if not errorlevel 1 (set "PY=py") else (set "PY=python")

%PY% tools\stage_pages.py || exit /b 1
echo.
echo Deployment site staged in .\_site
