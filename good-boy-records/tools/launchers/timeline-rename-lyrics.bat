@echo off
setlocal
cd /d "%~dp0..\.."
py -3 tools\timeline\rename_lyrics.py %*
exit /b %ERRORLEVEL%
