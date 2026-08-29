@echo off
setlocal EnableExtensions
cd /d "%~dp0\.."
if exist ".venv\Scripts\python.exe" (
  ".venv\Scripts\python.exe" -c "import moriyama_mail, flask, dotenv" >nul 2>&1
  if not errorlevel 1 exit /b 0
)
call "%~dp0setup_env.bat"
exit /b %ERRORLEVEL%
