@echo off
setlocal EnableExtensions
REM ASCII-only. Japanese Windows cmd.exe cannot run UTF-8 .bat files.

set "DEST=D:\dev\moriyama-mail-automation"
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"
set "REPO_URL=https://github.com/modafang111/moriyama-mail-automation.git"
set "REPO_BRANCH=cursor/mail-automation-phase1-b737"
set "CLONE_DIR=%TEMP%\moriyama-mail-automation-src"

echo Creating D:\dev ...
if not exist "D:\dev" mkdir "D:\dev"
if not exist "D:\dev" (
  echo Could not create D:\dev
  pause
  exit /b 1
)

if exist "%HERE%\pyproject.toml" (
  if /I not "%HERE%"=="%DEST%" (
    echo Copying files to %DEST% ...
    if not exist "%DEST%" mkdir "%DEST%"
    robocopy "%HERE%" "%DEST%" /E /XD .venv __pycache__ .pytest_cache /NFL /NDL /NJH /NJS
    if errorlevel 8 (
      echo Copy failed.
      pause
      exit /b 1
    )
  ) else (
    echo Already in %DEST%
  )
)

if not exist "%DEST%\pyproject.toml" (
  where git >nul 2>&1
  if errorlevel 1 (
    echo Git is not installed. https://git-scm.com/download/win
    echo Or download the ZIP and run this bat from the extracted folder.
    pause
    exit /b 1
  )
  echo Cloning from GitHub ...
  if exist "%CLONE_DIR%" rmdir /s /q "%CLONE_DIR%"
  git clone --branch "%REPO_BRANCH%" --single-branch "%REPO_URL%" "%CLONE_DIR%"
  if errorlevel 1 (
    echo Branch clone failed. Trying default branch ...
    if exist "%CLONE_DIR%" rmdir /s /q "%CLONE_DIR%"
    git clone "%REPO_URL%" "%CLONE_DIR%"
  )
  if not exist "%CLONE_DIR%\pyproject.toml" (
    echo Clone failed.
    pause
    exit /b 1
  )
  if not exist "%DEST%" mkdir "%DEST%"
  robocopy "%CLONE_DIR%" "%DEST%" /E /XD .venv __pycache__ .pytest_cache /NFL /NDL /NJH /NJS
  if errorlevel 8 (
    echo Copy failed.
    pause
    exit /b 1
  )
)

if not exist "%DEST%\pyproject.toml" (
  echo Program files were not found in %DEST%
  pause
  exit /b 1
)

cd /d "%DEST%"
call "%DEST%\scripts\setup_env.bat"
if errorlevel 1 (
  pause
  exit /b 1
)

echo.
echo Done. Next: run 03_start.bat
echo Folder: %DEST%
pause
endlocal
exit /b 0
