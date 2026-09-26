@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [GBR] Building Sonic Landscape...

if exist tools\import_showcase.py (
  echo [1/5] Refreshing showcase source data...
  py -3 tools\import_showcase.py
  if errorlevel 1 goto :error
) else (
  echo [1/5] import_showcase.py not present - using existing catalogue data.
)

set "INPUT="
if exist showcase-manifest.json set "INPUT=showcase-manifest.json"
if not defined INPUT if exist content-source\showcase-manifest.json set "INPUT=content-source\showcase-manifest.json"
if not defined INPUT if exist data\catalogue.json set "INPUT=data\catalogue.json"
if not defined INPUT if exist catalogue.json set "INPUT=catalogue.json"

if not defined INPUT (
  echo ERROR: Could not find a catalogue input.
  goto :error
)

if not exist templates\music_genre_taxonomy.csv (
  echo ERROR: templates\music_genre_taxonomy.csv is missing.
  goto :error
)
if not exist templates\landscape.html (
  echo ERROR: templates\landscape.html is missing.
  goto :error
)

if not exist _site mkdir _site

echo [2/5] Enriching %INPUT% with genre taxonomy...
py -3 tools\build_genre_catalogue.py "%INPUT%" templates\music_genre_taxonomy.csv _site\catalogue.json
if errorlevel 1 goto :error

echo [3/6] Publishing showcase media into _site...
if exist showcase (
  if exist _site\showcase rmdir /s /q _site\showcase
  xcopy /e /i /y showcase _site\showcase >nul
  if errorlevel 1 goto :error
) else (
  echo WARNING: showcase directory is missing. Direct media URLs will not work.
)

echo [4/6] Staging Sonic Landscape...
copy /y templates\landscape.html _site\landscape.html >nul
if errorlevel 1 goto :error

echo [5/6] Making Sonic Landscape the route index...
copy /y templates\landscape.html _site\index.html >nul
if errorlevel 1 goto :error

echo [6/6] Verifying output...
if not exist _site\index.html goto :error
if not exist _site\landscape.html goto :error
if not exist _site\catalogue.json goto :error

echo.
echo DONE: _site\index.html is now the Sonic Landscape.
echo Local test: py -3 -m http.server 8000
 echo Open: http://localhost:8000/_site/
exit /b 0

:error
echo.
echo BUILD FAILED.
exit /b 1
