@echo off
setlocal
cd /d "%~dp0"
py -3 tools\normalize_source_names.py
if errorlevel 1 exit /b %errorlevel%
py -3 tools\test_player.py
