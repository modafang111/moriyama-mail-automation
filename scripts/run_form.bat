@echo off
setlocal
cd /d "%~dp0\.."
if not exist ".venv\Scripts\python.exe" call "%~dp0setup_env.bat"
if not exist ".env" copy /Y ".env.example" ".env" >nul
echo Web form: http://127.0.0.1:8787/
start "" cmd /c "timeout /t 2 /nobreak >nul & start http://127.0.0.1:8787/"
".venv\Scripts\python.exe" -m moriyama_mail.intake.webapp
endlocal
