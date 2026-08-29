@echo off
setlocal
cd /d "%~dp0"
if not exist "pyproject.toml" (
  echo 先に「01_フォルダを作って配置.bat」を実行してください。
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
