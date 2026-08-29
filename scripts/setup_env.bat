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
  echo Python が見つかりません。
  echo https://www.python.org/downloads/ からインストールし、
  echo 「Add python.exe to PATH」にチェックを入れてください。
  exit /b 1
)

if not exist ".venv\Scripts\python.exe" (
  echo 仮想環境を作成しています...
  %PYLAUNCHER% -m venv .venv
  if errorlevel 1 exit /b 1
)

echo 必要な部品を入れています...
".venv\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install -r requirements.txt
if errorlevel 1 exit /b 1
".venv\Scripts\python.exe" -m pip install -e .
if errorlevel 1 exit /b 1

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
  echo .env を作成しました。必要なら後から編集してください。
)

echo.
echo セットアップが終わりました。
echo 配置場所: %CD%
endlocal
exit /b 0
