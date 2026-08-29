@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" call "%~dp0setup_env.bat"
if not exist ".env" copy /Y ".env.example" ".env" >nul
echo 顧客向けフォームを起動します。ブラウザで http://127.0.0.1:8787/ を開いてください。
".venv\Scripts\python.exe" -m moriyama_mail.intake.webapp
endlocal
