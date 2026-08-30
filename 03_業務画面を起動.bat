@echo off
setlocal
cd /d "%~dp0"
if not exist "pyproject.toml" (
  echo First run 01_setup.bat
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" call "%~dp0scripts\setup_env.bat"
call "%~dp0scripts\run_windows.bat"
endlocal
