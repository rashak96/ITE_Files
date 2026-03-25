@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH.
  echo Install Python, then try again.
  pause
  exit /b 1
)

echo Starting ITE quiz...
echo.
echo This will open the presenter in your browser automatically.
echo Keep this window open while presenting.
echo.

python run_live.py --lan-only

if errorlevel 1 (
  echo.
  echo Quiz launcher exited with an error.
  pause
)

