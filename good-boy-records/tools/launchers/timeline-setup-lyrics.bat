@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
set "RC=0"

set "VENV=.venv-whisperx"
set "PY=%VENV%\Scripts\python.exe"

rem Override if this machine needs another official PyTorch CUDA wheel channel.
if not defined GBR_TORCH_INDEX_URL set "GBR_TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128"

echo ========================================
echo GBR LYRIC ALIGNMENT ENVIRONMENT
echo ========================================
echo Environment: %VENV%
echo Torch index: %GBR_TORCH_INDEX_URL%
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Windows Python launcher "py" was not found.
  set "RC=1"
  goto :finish
)

if not exist "%PY%" (
  echo [1/5] Creating virtual environment...
  py -3 -m venv "%VENV%"
  if errorlevel 1 (
    set "RC=%ERRORLEVEL%"
    goto :finish
  )
) else (
  echo [1/5] Existing virtual environment found.
)

echo [2/5] Updating pip/build tooling...
"%PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 (
  set "RC=%ERRORLEVEL%"
  goto :finish
)

echo [3/5] Installing WhisperX / Demucs / YAML support...
"%PY%" -m pip install --upgrade -r tools\timeline\requirements-lyrics.txt
if errorlevel 1 (
  set "RC=%ERRORLEVEL%"
  goto :finish
)

echo [4/5] Forcing matching CUDA PyTorch LAST...
"%PY%" -m pip install --upgrade --force-reinstall torch==2.8.0 torchvision==0.23.0 torchaudio==2.8.0 --index-url "%GBR_TORCH_INDEX_URL%"
if errorlevel 1 (
  echo ERROR: CUDA PyTorch installation failed.
  set "RC=%ERRORLEVEL%"
  goto :finish
)

echo [5/5] Checking environment...
"%PY%" -c "import torch, yaml, demucs, whisperx; print('torch:', torch.__version__); print('cuda:', torch.version.cuda); print('cuda available:', torch.cuda.is_available()); print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE'); raise SystemExit(0 if torch.cuda.is_available() else 3)"
set "RC=%ERRORLEVEL%"
if not "%RC%"=="0" (
  echo ERROR: Environment installed but CUDA is not available.
  goto :finish
)

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo WARNING: ffmpeg was not found on PATH.
)

echo Environment ready.

:finish
echo.
if "%RC%"=="0" (
  echo Lyric environment setup finished successfully.
) else (
  echo ERROR: Lyric environment setup failed with exit code %RC%.
)
if not defined GBR_NO_PAUSE pause
exit /b %RC%
