@echo off
setlocal
cd /d "%~dp0"
if not exist "pyproject.toml" (
  echo First run 01_setup.bat
  pause
  exit /b 1
)
call "%~dp0scripts\setup_env.bat"
if errorlevel 1 (
  pause
  exit /b 1
)
pause
endlocal
