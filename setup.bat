@echo off
setlocal

cd /d "%~dp0"

echo Creating virtual environment in .venv...
py -m venv .venv
if errorlevel 1 (
  echo Failed to create virtual environment.
  exit /b 1
)

echo Activating virtual environment...
call .venv\Scripts\activate.bat
if errorlevel 1 (
  echo Failed to activate virtual environment.
  exit /b 1
)

echo Installing dependencies from root requirements.txt...
python -m pip install --upgrade pip
if errorlevel 1 (
  echo Failed to upgrade pip.
  exit /b 1
)

python -m pip install -r requirements.txt
if errorlevel 1 (
  echo Failed to install requirements.
  exit /b 1
)

echo Setup completed successfully.
exit /b 0
