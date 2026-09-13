@echo off
setlocal
cd /d "%~dp0"

echo ================================================================
echo  GOOD BOY RECORDS - BUILD CURATED SHOWCASE
echo ================================================================
echo Source: %CD%\showcase\
echo Nothing outside that folder will be scanned.
echo.

where py >nul 2>nul
if not errorlevel 1 (
  set "PY=py"
) else (
  set "PY=python"
)

rem _site is deployment output only. Remove any stale local deployment copy so
rem normal preview never carries a second complete set of the audio.
%PY% tools\clean_local_stage.py || goto :fail
%PY% tools\import_showcase.py || goto :fail
%PY% tools\prepare_artwork.py masters assets\img\sleeves || goto :fail
%PY% tools\build_catalogue.py || goto :fail
%PY% tools\check_audio_storage.py || goto :fail
%PY% tools\test_player.py || goto :fail
%PY% tools\test_matrix_lab.py || goto :fail
%PY% tools\check_links.py || goto :fail

echo.
echo Showcase build complete.
echo Local preview uses curated audio directly from .\showcase\; _site was not duplicated.
exit /b 0

:fail
echo.
echo BUILD FAILED.
exit /b 1
