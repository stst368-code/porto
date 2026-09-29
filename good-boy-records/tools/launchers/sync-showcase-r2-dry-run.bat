@echo off
setlocal
cd /d "%~dp0..\.."
set "R2_REMOTE=r2"
set "R2_BUCKET=good-boy-records"
echo DRY RUN ONLY - shows remote deletions/changes required for an exact mirror.
rclone sync "showcase" "%R2_REMOTE%:%R2_BUCKET%/showcase" --dry-run --progress
