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

echo Starting ITE quiz for ANYWHERE access...
echo.
echo Keep this window open while presenting.
echo It will print:
echo   - Presenter URL (open on any PC)
echo   - Audience /vote URL
echo.

python run_live.py

if errorlevel 1 (
  echo.
  echo Quiz launcher exited with an error.
  pause
)

