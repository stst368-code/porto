@echo off
setlocal
cd /d "%~dp0"

echo [GBR] Building Sonic Landscape...

if exist tools\import_showcase.py (
  echo [1/4] Refreshing showcase manifest...
  py -3 tools\import_showcase.py
  if errorlevel 1 goto :error
)

set "INPUT="
if exist showcase-manifest.json set "INPUT=showcase-manifest.json"
if not defined INPUT if exist data\catalogue.json set "INPUT=data\catalogue.json"
if not defined INPUT if exist catalogue.json set "INPUT=catalogue.json"

if not defined INPUT (
  echo ERROR: Could not find showcase-manifest.json, data\catalogue.json, or catalogue.json
  goto :error
)

if not exist templates\music_genre_taxonomy.csv (
  echo ERROR: templates\music_genre_taxonomy.csv is missing
  goto :error
)

if not exist _site mkdir _site

echo [2/4] Enriching %INPUT% with genre taxonomy...
py -3 tools\build_genre_catalogue.py "%INPUT%" templates\music_genre_taxonomy.csv _site\catalogue.json
if errorlevel 1 goto :error

echo [3/4] Landscape page already staged in _site\landscape.html

if not exist _site\index.html (
  copy /y _site\landscape.html _site\index.html >nul
  echo [4/4] No site index existed, so landscape.html was also copied to index.html
) else (
  echo [4/4] Existing _site\index.html preserved
)

echo.
echo DONE.
echo Serve the repo root with: py -3 -m http.server 8000
echo Then open: http://localhost:8000/_site/landscape.html
exit /b 0

:error
echo.
echo BUILD FAILED.
exit /b 1
