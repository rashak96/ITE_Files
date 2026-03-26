@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH.
  pause
  exit /b 1
)

echo Simple presenter: big buttons, polls built into the flow (same /vote for phones).
echo.
python run_live.py --simple

if errorlevel 1 pause
