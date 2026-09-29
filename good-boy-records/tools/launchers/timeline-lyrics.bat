@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "RC=0"
set "PY="

rem Optional: reuse an existing external WhisperX environment without moving it.
if defined GBR_WHISPERX_PYTHON (
  if exist "%GBR_WHISPERX_PYTHON%" (
    set "PY=%GBR_WHISPERX_PYTHON%"
  ) else (
    echo ERROR: GBR_WHISPERX_PYTHON points to a missing file:
    echo        %GBR_WHISPERX_PYTHON%
    set "RC=2"
    goto :finish
  )
)

rem Preferred permanent setup: repo-local virtual environment.
if not defined PY if exist ".venv-whisperx\Scripts\python.exe" set "PY=.venv-whisperx\Scripts\python.exe"

if not defined PY (
  echo ERROR: No WhisperX environment is configured.
  echo.
  echo Recommended:
  echo   tools\launchers\timeline-setup-lyrics.bat
  set "RC=2"
  goto :finish
)

"%PY%" -c "import torch, yaml, demucs, whisperx" >nul 2>nul
if errorlevel 1 (
  echo ERROR: The selected Python does not have the required lyric-alignment packages.
  echo Python: %PY%
  echo Run tools\launchers\timeline-setup-lyrics.bat to rebuild the repo-local environment.
  set "RC=2"
  goto :finish
)

"%PY%" tools\timeline\lyrics.py %*
set "RC=%ERRORLEVEL%"

:finish
echo.
if "%RC%"=="0" (
  echo Lyric alignment finished successfully.
) else (
  echo ERROR: Lyric alignment failed with exit code %RC%.
)
if not defined GBR_NO_PAUSE pause
exit /b %RC%
