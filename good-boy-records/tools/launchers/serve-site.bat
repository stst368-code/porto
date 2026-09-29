@echo off
setlocal
cd /d "%~dp0..\.."
if not exist _site\index.html (
  call tools\launchers\build-site.bat || exit /b 1
)
start "" http://localhost:8000/_site/
py -3 -m http.server 8000
