@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" call "%~dp0setup_env.bat"
if errorlevel 1 (
  pause
  exit /b 1
)
if not exist ".env" copy /Y ".env.example" ".env" >nul
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
set "MORIYAMA_INSTALL_DIR=%CD%"
".venv\Scripts\python.exe" -c "import tkinter, flask, dotenv, moriyama_mail"
if errorlevel 1 (
  echo Setup is incomplete. Run 02_install.bat
  pause
  exit /b 1
)
".venv\Scripts\python.exe" -m moriyama_mail
if errorlevel 1 (
  echo Failed to start.
  pause
  exit /b 1
)
endlocal
