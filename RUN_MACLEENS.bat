@echo off
setlocal
cd /d "%~dp0"
title Macleen's Food House System
set "PYTHONUTF8=1"

set "PYTHON_CMD="
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import flask, flask_sqlalchemy" >nul 2>&1
  if not errorlevel 1 set "PYTHON_CMD=.venv\Scripts\python.exe"
)

if not defined PYTHON_CMD (
  where py >nul 2>&1
  if errorlevel 1 (
    echo Python was not found. Install Python 3.14, then run this file again.
    pause
    exit /b 1
  )
  echo Preparing a clean local environment...
  if not exist ".venv_macleens\Scripts\python.exe" py -3.14 -m venv .venv_macleens
  if errorlevel 1 (
    echo Could not create the Python environment.
    pause
    exit /b 1
  )
  set "PYTHON_CMD=.venv_macleens\Scripts\python.exe"
)

echo Installing or checking required packages...
"%PYTHON_CMD%" -m pip install -r requirements.txt
if errorlevel 1 (
  echo Package installation failed. Check your internet connection and try again.
  pause
  exit /b 1
)

echo Running safety checks...
"%PYTHON_CMD%" scripts\predeploy_check.py
if errorlevel 1 (
  echo Safety checks failed. The system was not started.
  pause
  exit /b 1
)

echo Running isolated Community behavior checks...
"%PYTHON_CMD%" scripts\community_smoke_check.py
if errorlevel 1 (
  echo Community checks failed. The system was not started.
  pause
  exit /b 1
)

echo Running Financial Statements and Bundle Deals checks...
"%PYTHON_CMD%" scripts\financial_bundle_smoke_check.py
if errorlevel 1 (
  echo Financial Statements or Bundle Deals checks failed. The system was not started.
  pause
  exit /b 1
)

echo Running Digital Assets, GCash, and Help Bot checks...
"%PYTHON_CMD%" scripts\digital_assets_gateway_smoke_check.py
if errorlevel 1 (
  echo Digital Assets, GCash, or Help Bot checks failed. The system was not started.
  pause
  exit /b 1
)

echo Starting Macleen's Food House at http://127.0.0.1:5000
start "" http://127.0.0.1:5000
"%PYTHON_CMD%" app.py

if errorlevel 1 (
  echo The application stopped because of an error.
  pause
)
endlocal
