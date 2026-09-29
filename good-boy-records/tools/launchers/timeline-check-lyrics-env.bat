@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "RC=0"

set "PY="
if defined GBR_WHISPERX_PYTHON if exist "%GBR_WHISPERX_PYTHON%" set "PY=%GBR_WHISPERX_PYTHON%"
if not defined PY if exist ".venv-whisperx\Scripts\python.exe" set "PY=.venv-whisperx\Scripts\python.exe"

if not defined PY (
  echo ERROR: No lyric environment configured.
  set "RC=2"
  goto :finish
)

echo Python: %PY%
"%PY%" -c "import sys, torch, yaml, demucs, whisperx; print('python:',sys.version); print('torch:',torch.__version__); print('cuda:',torch.version.cuda); print('cuda available:',torch.cuda.is_available()); print('gpu:',torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE'); print('whisperx: OK'); print('demucs: OK'); print('yaml: OK')"
set "RC=%ERRORLEVEL%"

:finish
echo.
if "%RC%"=="0" (
  echo Lyric environment check passed.
) else (
  echo ERROR: Lyric environment check failed with exit code %RC%.
)
if not defined GBR_NO_PAUSE pause
exit /b %RC%
