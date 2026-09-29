@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."

set "VENV=.venv-whisperx"
set "PY=%VENV%\Scripts\python.exe"

rem Override this if this machine needs another official PyTorch CUDA wheel channel.
rem Example:
rem   set GBR_TORCH_INDEX_URL=https://download.pytorch.org/whl/cu126
if not defined GBR_TORCH_INDEX_URL (
  set "GBR_TORCH_INDEX_URL=https://download.pytorch.org/whl/cu128"
)

echo ========================================
echo GBR LYRIC ALIGNMENT ENVIRONMENT
echo ========================================
echo.
echo Environment: %VENV%
echo Torch index: %GBR_TORCH_INDEX_URL%
echo.

where py >nul 2>nul
if errorlevel 1 (
  echo ERROR: Windows Python launcher "py" was not found.
  exit /b 1
)

if not exist "%PY%" (
  echo [1/5] Creating virtual environment...
  py -3 -m venv "%VENV%"
  if errorlevel 1 exit /b 1
) else (
  echo [1/5] Existing virtual environment found.
)

echo [2/5] Updating pip/build tooling...
"%PY%" -m pip install --upgrade pip setuptools wheel
if errorlevel 1 exit /b 1

echo [3/5] Installing GPU PyTorch...
"%PY%" -m pip install --upgrade torch torchaudio --index-url "%GBR_TORCH_INDEX_URL%"
if errorlevel 1 (
  echo.
  echo ERROR: PyTorch installation failed.
  echo Set GBR_TORCH_INDEX_URL to the appropriate official PyTorch CUDA wheel channel and rerun.
  exit /b 1
)

echo [4/5] Installing WhisperX / Demucs / YAML support...
"%PY%" -m pip install --upgrade -r tools\timeline\requirements-lyrics.txt
if errorlevel 1 exit /b 1

echo [5/5] Checking environment...
"%PY%" -c "import torch, yaml, demucs, whisperx; print('torch:', torch.__version__); print('cuda:', torch.version.cuda); print('cuda available:', torch.cuda.is_available()); print('gpu:', torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'NONE')"
if errorlevel 1 exit /b 1

where ffmpeg >nul 2>nul
if errorlevel 1 (
  echo.
  echo WARNING: ffmpeg was not found on PATH.
  echo WhisperX/Demucs may require FFmpeg for some audio formats.
)

echo.
echo Environment ready.
echo Run:
echo   tools\launchers\timeline-lyrics.bat --track song-name
echo or:
echo   tools\launchers\timeline-all.bat
