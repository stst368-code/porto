@echo off
setlocal
cd /d "%~dp0"

echo Applying GBR conveyor catalogue layout...

echo.
echo This patch updates:
echo   assets\css\studio.css
echo   assets\js\studio.js
echo   tools\test_player.py

echo.
echo Running regression checks if the full project is present...
if exist "tools\test_player.py" if exist "index.html" (
    py -3 tools\test_player.py
    if errorlevel 1 goto :error
) else (
    echo Full project files were not found in this patch folder.
    echo Extract this ZIP over the Good Boy Records project root first.
)

echo.
echo Conveyor catalogue layout applied.
exit /b 0

:error
echo.
echo Regression checks failed. Review the output above.
exit /b 1
