@echo off
setlocal
cd /d "%~dp0"
if not exist "pyproject.toml" (
  echo 先に「01_フォルダを作って配置.bat」を実行してください。
  pause
  exit /b 1
)
if not exist ".venv\Scripts\python.exe" call "%~dp0scripts\setup_env.bat"
call "%~dp0scripts\run_windows.bat"
endlocal
