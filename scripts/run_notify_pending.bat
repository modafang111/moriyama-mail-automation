@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" call "%~dp0ensure_venv.bat"
if errorlevel 1 exit /b 1
set "PYTHONPATH=%CD%\src;%PYTHONPATH%"
set "MORIYAMA_INSTALL_DIR=%CD%"
".venv\Scripts\python.exe" scripts\notify_wordpress_pending.py %*
exit /b %ERRORLEVEL%
