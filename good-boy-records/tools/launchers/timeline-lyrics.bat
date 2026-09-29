@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."

set "PY="

rem Optional: reuse an existing external WhisperX environment without moving it.
if defined GBR_WHISPERX_PYTHON (
  if exist "%GBR_WHISPERX_PYTHON%" (
    set "PY=%GBR_WHISPERX_PYTHON%"
  ) else (
    echo ERROR: GBR_WHISPERX_PYTHON points to a missing file:
    echo        %GBR_WHISPERX_PYTHON%
    exit /b 2
  )
)

rem Preferred permanent setup: repo-local virtual environment.
if not defined PY (
  if exist ".venv-whisperx\Scripts\python.exe" (
    set "PY=.venv-whisperx\Scripts\python.exe"
  )
)

if not defined PY (
  echo ERROR: No WhisperX environment is configured.
  echo.
  echo Recommended:
  echo   tools\launchers\timeline-setup-lyrics.bat
  echo.
  echo Or temporarily reuse the old environment without moving it:
  echo   set "GBR_WHISPERX_PYTHON=C:\path\to\old\venv\Scripts\python.exe"
  echo   tools\launchers\timeline-lyrics.bat
  echo.
  exit /b 2
)

"%PY%" -c "import torch, yaml, demucs, whisperx" >nul 2>nul
if errorlevel 1 (
  echo ERROR: The selected Python does not have the required lyric-alignment packages.
  echo Python: %PY%
  echo Run tools\launchers\timeline-setup-lyrics.bat to rebuild the repo-local environment.
  exit /b 2
)

"%PY%" tools\timeline\lyrics.py %*
exit /b %ERRORLEVEL%
