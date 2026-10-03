@echo off
setlocal
cd /d "%~dp0..\.."
set "R2_REMOTE=r2"
set "R2_BUCKET=good-boy-records"

where rclone >nul 2>nul || (
  echo ERROR: rclone is not installed or not on PATH.
  exit /b 1
)
if not exist showcase\NUL (
  echo ERROR: showcase folder not found.
  exit /b 1
)

echo Uploading changed/new showcase files...
rclone copy "showcase" "%R2_REMOTE%:%R2_BUCKET%/showcase" -L --progress --create-empty-src-dirs || exit /b 1

echo Verifying local files exist remotely...
rclone check "showcase" "%R2_REMOTE%:%R2_BUCKET%/showcase" -L --one-way

echo Done. Remote-only stale files are intentionally left alone.
