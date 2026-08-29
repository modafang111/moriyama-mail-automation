@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."

set "PYLAUNCHER="
where py >nul 2>&1
if not errorlevel 1 (
  py -3 -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
  if not errorlevel 1 set "PYLAUNCHER=py -3"
)
if not defined PYLAUNCHER (
  where python >nul 2>&1
  if not errorlevel 1 (
    python -c "import sys; raise SystemExit(0 if sys.version_info >= (3,11) else 1)" >nul 2>&1
    if not errorlevel 1 set "PYLAUNCHER=python"
  )
)
if not defined PYLAUNCHER (
  echo Python 3.11 or newer was not found.
  echo Install from https://www.python.org/downloads/
  echo Check "Add python.exe to PATH" during install.
  exit /b 1
)

%PYLAUNCHER% scripts\setup_local.py
if errorlevel 1 exit /b 1
endlocal
exit /b 0
