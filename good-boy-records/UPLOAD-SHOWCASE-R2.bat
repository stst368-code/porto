@echo off
setlocal EnableExtensions
cd /d "%~dp0"

rem Configure these two values after running: rclone config
set "R2_REMOTE=r2"
set "R2_BUCKET=good-boy-records"

where rclone >nul 2>&1 || (
  echo ERROR: rclone is not installed or not on PATH.
  exit /b 1
)
if not exist showcase\NUL (
  echo ERROR: showcase\ was not found beside this script.
  exit /b 1
)

echo Uploading local showcase\ to %R2_REMOTE%:%R2_BUCKET%/showcase ...
rclone copy "showcase" "%R2_REMOTE%:%R2_BUCKET%/showcase" --progress --create-empty-src-dirs
if errorlevel 1 exit /b 1

echo.
echo Verifying uploaded files...
rclone check "showcase" "%R2_REMOTE%:%R2_BUCKET%/showcase" --one-way
if errorlevel 1 exit /b 1

echo.
echo Upload and verification complete.
exit /b 0
