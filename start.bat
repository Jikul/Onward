@echo off
title Onward
cd /d "%~dp0"
set PY=python
where py >nul 2>nul && set PY=py -3
%PY% --version >nul 2>nul
if errorlevel 1 (
  echo.
  echo Python was not found. Install Python 3.11 or newer from https://www.python.org/downloads/
  echo and tick "Add python.exe to PATH" during the install. Then run this file again.
  pause
  exit /b
)
set EXTRA=
:run
echo Checking the Python packages (SimConnect, Pillow, certifi)...
%PY% -m pip install --disable-pip-version-check -q -r requirements.txt
echo Starting Onward. Keep this window open while you fly.
%PY% server.py %* %EXTRA%
rem Exit code 3 means "updated, start again" (the browser tab is already open)
if errorlevel 3 if not errorlevel 4 (
  set EXTRA=--no-browser
  echo.
  echo Restarting Onward...
  goto run
)
pause
