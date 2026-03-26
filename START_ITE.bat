@echo off
title ITE Live
cd /d "%~dp0"
where python >nul 2>nul || (echo Install Python and add it to PATH. & pause & exit /b 1)

echo One step: server + simple presenter in browser (phones use /vote from the URL it prints).
echo.
python run_live.py --simple
if errorlevel 1 pause
