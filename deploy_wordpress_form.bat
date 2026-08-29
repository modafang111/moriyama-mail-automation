@echo off
setlocal EnableExtensions
cd /d "%~dp0"
if not exist "pyproject.toml" (
  echo First run 01_setup.bat
  pause
  exit /b 1
)
call "%~dp0scripts\run_deploy_wordpress.bat"
if errorlevel 1 (
  echo Deploy failed. Check .env FTP settings and WORDPRESS_INTAKE_TOKEN.
  pause
  exit /b 1
)
echo.
echo Form: https://wordpress-123.com/mail-request/
pause
endlocal
