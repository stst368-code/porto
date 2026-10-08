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

echo [1/6] Building compact catalogue directly from showcase...
py -3 tools\build_catalogue.py --output data\catalogue.json || exit /b 1

echo [2/6] Refreshing Easter catalogue from the actual R2 showcase/easter contents...
if exist tools\augment_easter_catalogue.py (
  py -3 tools\augment_easter_catalogue.py data\catalogue.json . || exit /b 1
)
copy /y data\catalogue.json _site\catalogue.json >nul || exit /b 1

echo [3/6] Building knowledge manifest...
if exist content-source\folders (
  mkdir _site\content-source 2>nul
  xcopy /e /i /y content-source\folders _site\content-source\folders >nul || exit /b 1
)
py -3 tools\build_knowledge_manifest.py _site\knowledge-manifest.json || exit /b 1

echo [4/6] Staging player...
copy /y showcase-host.js _site\showcase-host.js >nul || exit /b 1
copy /y templates\landscape.html _site\landscape.html >nul || exit /b 1
copy /y templates\landscape.html _site\index.html >nul || exit /b 1

echo [5/6] Staging research analytics...
if not exist analytics\index.html (
  echo ERROR: analytics\index.html missing. Copy the analytics page from the update package.
  exit /b 1
)
if not exist data\analytics\generations.json (
  echo ERROR: Analytics export missing. Run tools\launchers\refresh-analytics.ps1
  exit /b 1
)
if not exist data\analytics\summary.json (
  echo ERROR: Analytics summary missing. Run tools\launchers\refresh-analytics.ps1
  exit /b 1
)
mkdir _site\analytics 2>nul
mkdir _site\data\analytics 2>nul
copy /y analytics\index.html _site\analytics\index.html >nul || exit /b 1
copy /y analytics\analytics.js _site\analytics\analytics.js >nul || exit /b 1
copy /y analytics\analytics.css _site\analytics\analytics.css >nul || exit /b 1
copy /y data\analytics\generations.json _site\data\analytics\generations.json >nul || exit /b 1
copy /y data\analytics\summary.json _site\data\analytics\summary.json >nul || exit /b 1

echo [6/6] Adding analytics navigation and verifying...
py -3 tools\analytics\inject_link.py _site\index.html _site\landscape.html || exit /b 1
if exist _site\showcase (
  echo ERROR: _site\showcase must not exist; media belongs on R2.
  exit /b 1
)
if not exist _site\catalogue.json exit /b 1
if not exist _site\knowledge-manifest.json exit /b 1
if not exist _site\showcase-host.js exit /b 1
if not exist _site\index.html exit /b 1
if not exist _site\analytics\index.html exit /b 1
if not exist _site\data\analytics\generations.json exit /b 1

echo.
echo DONE: _site is ready.
echo Preview with tools\launchers\serve-site.bat
