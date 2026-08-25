@echo off
cd /d "%~dp0"
where python >nul 2>nul
if errorlevel 1 (
  echo [AHK_Filter] Python was not found on PATH.
  echo Please install Python 3.10+ from https://www.python.org/downloads/
  echo Make sure "Add python.exe to PATH" is checked.
  pause
  exit /b 1
)
python -c "import customtkinter,pynput,win32gui" 1>nul 2>nul
if errorlevel 1 (
  echo [AHK_Filter] Installing Python dependencies...
  python -m pip install -r requirements.txt
  if errorlevel 1 (
    echo Dependency install failed.
    pause
    exit /b 1
  )
)
python run.py %*
if errorlevel 1 pause
