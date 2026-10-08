@echo off
setlocal
cd /d "%~dp0..\.."
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "tools\launchers\refresh-analytics.ps1" %*
if errorlevel 1 pause
