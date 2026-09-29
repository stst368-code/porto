@echo off
setlocal EnableExtensions
cd /d "%~dp0"

echo [GBR] Building Sonic Landscape with external showcase media support...

if exist showcase\NUL (
  if exist tools\import_showcase.py (
    echo [1/7] Importing local showcase metadata...
    py -3 tools\import_showcase.py || goto :error
  )
  if exist tools\prepare_artwork.py if exist masters\NUL (
    echo [2/7] Preparing local artwork derivatives for fallback/preview...
    py -3 tools\prepare_artwork.py masters assets\img\sleeves || goto :error
  )
  if exist tools\build_catalogue.py (
    echo [3/7] Refreshing compact catalogue...
    py -3 tools\build_catalogue.py || goto :error
  )
) else (
  echo [1-3/7] Local showcase not present - using committed data\catalogue.json.
)

set "INPUT="
if exist data\catalogue.json set "INPUT=data\catalogue.json"
if not defined INPUT if exist showcase-manifest.json set "INPUT=showcase-manifest.json"
if not defined INPUT if exist content-source\showcase-manifest.json set "INPUT=content-source\showcase-manifest.json"
if not defined INPUT if exist catalogue.json set "INPUT=catalogue.json"
if not defined INPUT (
  echo ERROR: Could not find a catalogue input. Build once locally while showcase\ is present and commit data\catalogue.json.
  goto :error
)
if not exist templates\music_genre_taxonomy.csv goto :error
if not exist templates\landscape.html goto :error
if not exist _site mkdir _site

echo [4/7] Building genre-enriched catalogue from %INPUT%...
py -3 tools\build_genre_catalogue.py "%INPUT%" templates\music_genre_taxonomy.csv _site\catalogue.json || goto :error
if exist tools\augment_easter_catalogue.py py -3 tools\augment_easter_catalogue.py _site\catalogue.json . || goto :error

echo [5/7] Publishing small site assets only - showcase media stays external...
if exist content-source\folders (
  if not exist _site\content-source mkdir _site\content-source
  if exist _site\content-source\folders rmdir /s /q _site\content-source\folders
  xcopy /e /i /y content-source\folders _site\content-source\folders >nul || goto :error
)
echo [5b/7] Indexing knowledge markdown...
py -3 tools\build_knowledge_manifest.py _site\knowledge-manifest.json || goto :error
copy /y showcase-host.js _site\showcase-host.js >nul || goto :error

echo [6/7] Staging Sonic Landscape...
copy /y templates\landscape.html _site\landscape.html >nul || goto :error
copy /y templates\landscape.html _site\index.html >nul || goto :error

echo [7/7] Verifying output contains no showcase media...
if exist _site\showcase (
  echo ERROR: _site\showcase exists; external-media build must not stage it.
  goto :error
)
if not exist _site\catalogue.json goto :error
if not exist _site\showcase-host.js goto :error
if not exist _site\knowledge-manifest.json goto :error

echo.
echo DONE: _site contains the player/catalogue only. showcase\ remains local/R2.
echo Local test: py -3 -m http.server 8000
echo Open: http://localhost:8000/_site/
exit /b 0

:error
echo.
echo BUILD FAILED.
exit /b 1
