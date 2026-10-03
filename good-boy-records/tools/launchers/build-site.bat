@echo off
setlocal EnableExtensions
cd /d "%~dp0..\.."

echo [GBR] Building Sonic site...

if not exist showcase\NUL (
  echo ERROR: Local showcase is missing.
  echo This launcher is the local-authoring build and expects good-boy-records\showcase.
  exit /b 1
)

if exist _site rmdir /s /q _site
mkdir _site || exit /b 1

echo [1/5] Building compact catalogue directly from showcase...
py -3 tools\build_catalogue.py --output data\catalogue.json || exit /b 1

echo [2/5] Refreshing Easter catalogue from the actual R2 showcase/easter contents...
if exist tools\augment_easter_catalogue.py (
  py -3 tools\augment_easter_catalogue.py data\catalogue.json . || exit /b 1
)
copy /y data\catalogue.json _site\catalogue.json >nul || exit /b 1

echo [3/5] Building knowledge manifest...
if exist content-source\folders (
  mkdir _site\content-source 2>nul
  xcopy /e /i /y content-source\folders _site\content-source\folders >nul || exit /b 1
)
py -3 tools\build_knowledge_manifest.py _site\knowledge-manifest.json || exit /b 1

echo [4/5] Staging player...
copy /y showcase-host.js _site\showcase-host.js >nul || exit /b 1
copy /y templates\landscape.html _site\landscape.html >nul || exit /b 1
copy /y templates\landscape.html _site\index.html >nul || exit /b 1

echo [5/5] Verifying...
if exist _site\showcase (
  echo ERROR: _site\showcase must not exist; media belongs on R2.
  exit /b 1
)
if not exist _site\catalogue.json exit /b 1
if not exist _site\knowledge-manifest.json exit /b 1
if not exist _site\showcase-host.js exit /b 1
if not exist _site\index.html exit /b 1

echo.
echo DONE: _site is ready.
echo Preview with tools\launchers\serve-site.bat
