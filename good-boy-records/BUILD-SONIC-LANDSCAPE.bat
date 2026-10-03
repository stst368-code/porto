@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Single supported build path. Keep this root launcher as a convenience wrapper
rem so it cannot drift away from tools\launchers\build-site.bat again.
call tools\launchers\build-site.bat
exit /b %errorlevel%
