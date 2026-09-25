@echo off
setlocal
cd /d "%~dp0"
if exist BUILD-SHOWCASE.bat (
    call BUILD-SHOWCASE.bat
    exit /b %errorlevel%
)
echo BUILD-SHOWCASE.bat was not found in this project root.
exit /b 1
