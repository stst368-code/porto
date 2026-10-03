@echo off
setlocal
cd /d "%~dp0..\.."
if not exist "showcase\NUL" (
  echo ERROR: showcase folder not found at %CD%\showcase
  pause
  exit /b 1
)
where py >nul 2>nul && (
  py -3 "tools\lyric-review\server.py"
  goto :done
)
where python >nul 2>nul || (
  echo ERROR: Python is not installed or not on PATH.
  pause
  exit /b 1
)
python "tools\lyric-review\server.py"
:done
if errorlevel 1 pause
