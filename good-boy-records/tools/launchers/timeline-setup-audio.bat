@echo off
setlocal
cd /d "%~dp0..\.."
if not exist ".venv-audio-analysis\Scripts\python.exe" (
  py -3 -m venv .venv-audio-analysis || exit /b 1
)
".venv-audio-analysis\Scripts\python.exe" -m pip install --upgrade pip || exit /b 1
".venv-audio-analysis\Scripts\python.exe" -m pip install -r tools\timeline\requirements-audio.txt || exit /b 1
echo Audio/dance environment ready.
