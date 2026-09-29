@echo off
setlocal
cd /d "%~dp0..\.."
py -3 tools\timeline\status.py %*
