@echo off
setlocal
cd /d "%~dp0..\.."
if exist ".venv-audio-analysis\Scripts\python.exe" (
  ".venv-audio-analysis\Scripts\python.exe" tools\timeline\playback.py %*
) else (
  py -3 tools\timeline\playback.py %*
)
exit /b %ERRORLEVEL%
