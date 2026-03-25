@echo off
setlocal
cd /d "%~dp0"

where python >nul 2>nul
if errorlevel 1 (
  echo Python was not found on PATH.
  pause
  exit /b 1
)

echo Building ITE_HTML from ite_data.json ...
python create_ite_html.py
if errorlevel 1 (
  echo create_ite_html.py failed.
  pause
  exit /b 1
)

echo.
echo Starting local poll server (keep this window open) ...
echo Open: http://127.0.0.1:8765/
echo Phones on same Wi-Fi: use your PC LAN IP instead of 127.0.0.1
echo.
python poll_server.py
pause
