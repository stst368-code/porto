@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."
py -3 tools\timeline\rename_lyrics.py %*
set "RC=%ERRORLEVEL%"
echo.
if "%RC%"=="0" (
  echo Lyric sidecar rename finished successfully.
) else (
  echo ERROR: Lyric sidecar rename failed with exit code %RC%.
)
if not defined GBR_NO_PAUSE pause
exit /b %RC%
