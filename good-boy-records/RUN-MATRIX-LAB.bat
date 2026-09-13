@echo off
setlocal
cd /d "%~dp0"

echo ================================================================
echo  GOOD BOY RECORDS - PARAMETER MATRIX LAB
echo ================================================================
echo Output: %CD%\content-source\otheraudio
 echo.

where py >nul 2>nul
if not errorlevel 1 (
  set "PY=py"
) else (
  set "PY=python"
)

if "%GBR_MINIMAX_TRACKS%"=="" (
  echo Enter the folder containing the MiniMax YAMLs you want to select from.
  echo You can set GBR_MINIMAX_TRACKS later to skip this prompt.
  set /p "GBR_MINIMAX_TRACKS=YAML root: "
)

if "%GBR_MINIMAX_TRACKS%"=="" (
  echo No YAML root supplied.
  exit /b 1
)
if not exist "%GBR_MINIMAX_TRACKS%" (
  echo YAML root does not exist: %GBR_MINIMAX_TRACKS%
  exit /b 1
)

%PY% tools\matrix_lab\minimax_matrix_runner.py ^
  --cfg tools\matrix_lab\minimax_matrix_runner.cfg ^
  --tracks-root "%GBR_MINIMAX_TRACKS%" ^
  --output-root "%CD%\content-source\otheraudio" %*

if errorlevel 1 exit /b 1

echo.
echo Matrix generation complete. Run BUILD-SHOWCASE.bat to mirror it into the site.
