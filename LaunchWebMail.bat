@echo off
setlocal

cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found. Please run setup.bat first.
  exit /b 1
)

echo Launching web mail application...
".venv\Scripts\python.exe" mailclient\app.py
