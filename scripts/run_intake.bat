@echo off
setlocal
cd /d "%~dp0\.."

if not exist ".venv\Scripts\python.exe" (
  echo Creating virtual environment...
  py -3 -m venv .venv
  ".venv\Scripts\python.exe" -m pip install --upgrade pip
  ".venv\Scripts\python.exe" -m pip install -r requirements.txt
)

if not exist ".env" (
  copy /Y ".env.example" ".env" >nul
)

echo 顧客向けフォームを起動します。
".venv\Scripts\python.exe" -m moriyama_mail.intake.webapp
endlocal
