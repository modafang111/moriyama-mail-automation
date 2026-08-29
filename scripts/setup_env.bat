@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PYLAUNCHER="
where py >nul 2>&1
if not errorlevel 1 set "PYLAUNCHER=py -3"
if not defined PYLAUNCHER (
  where python >nul 2>&1
  if not errorlevel 1 set "PYLAUNCHER=python"
)
if not defined PYLAUNCHER (
  echo Python was not found.
  echo Install from https://www.python.org/downloads/
  echo Check "Add python.exe to PATH" during install.
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtualenv ...
  %PYLAUNCHER% -m venv .venv
  if errorlevel 1 exit /b 1
)

echo Installing packages ...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 exit /b 1

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo Created .env
)

echo.
echo Setup finished.
echo Folder: %CD%
endlocal
exit /b 0
