@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."

set "PY=.venv-audio-analysis\Scripts\python.exe"
set "RC=0"

rem The analysis environment is deliberately separate from WhisperX.
rem If it is missing OR only half-installed, repair it automatically.
if not exist "%PY%" goto :repair

"%PY%" -c "import numpy, librosa, soundfile, yaml" >nul 2>nul
if errorlevel 1 goto :repair
goto :run

:repair
echo Audio-analysis dependencies are missing or incomplete.
echo Repairing .venv-audio-analysis before continuing...
echo.

setlocal
set "GBR_NO_PAUSE=1"
call tools\launchers\timeline-setup-audio.bat
set "SETUP_RC=%ERRORLEVEL%"
endlocal & set "SETUP_RC=%SETUP_RC%"

if not "%SETUP_RC%"=="0" (
  set "RC=%SETUP_RC%"
  goto :finish
)

if not exist "%PY%" (
  echo ERROR: Audio setup completed but %PY% was not created.
  set "RC=2"
  goto :finish
)

"%PY%" -c "import numpy, librosa, soundfile, yaml"
if errorlevel 1 (
  echo ERROR: Audio environment still cannot import required packages.
  set "RC=%ERRORLEVEL%"
  goto :finish
)

:run
"%PY%" tools\timeline\audio.py %*
set "RC=%ERRORLEVEL%"

:finish
echo.
if "%RC%"=="0" (
  echo Audio analysis finished successfully.
) else (
  echo ERROR: Audio analysis failed with exit code %RC%.
)
if not defined GBR_NO_PAUSE pause
exit /b %RC%
