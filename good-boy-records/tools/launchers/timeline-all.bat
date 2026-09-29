@echo off
setlocal
cd /d "%~dp0..\.."
call tools\launchers\timeline-lyrics.bat %*
if errorlevel 1 exit /b %ERRORLEVEL%
call tools\launchers\timeline-audio.bat %*
if errorlevel 1 exit /b %ERRORLEVEL%
call tools\launchers\timeline-playback.bat %*
exit /b %ERRORLEVEL%
