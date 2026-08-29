@echo off
setlocal EnableExtensions
REM ローカルPCに D:\dev が無くても、このファイルを実行すれば配置できます。
REM 使い方:
REM  1. GitHub から ZIP を展開したフォルダ、または git clone したフォルダで実行する
REM  2. もしくは、このファイルだけ先に保存して実行すると git clone します

set "DEST=D:\dev\moriyama-mail-automation"
set "HERE=%~dp0"
if "%HERE:~-1%"=="\" set "HERE=%HERE:~0,-1%"
set "REPO_URL=https://github.com/modafang111/moriyama-mail-automation.git"

echo D:\dev を作成します。
if not exist "D:\dev" mkdir "D:\dev"
if not exist "D:\dev" (
  echo D:\dev を作れませんでした。
  pause
  exit /b 1
)

if exist "%HERE%\pyproject.toml" (
  if /I not "%HERE%"=="%DEST%" (
    echo プログラムを %DEST% へコピーします。
    if not exist "%DEST%" mkdir "%DEST%"
    robocopy "%HERE%" "%DEST%" /E /XD .venv __pycache__ .pytest_cache /NFL /NDL /NJH /NJS
    if errorlevel 8 (
      echo コピーに失敗しました。
      pause
      exit /b 1
    )
  ) else (
    echo すでに %DEST% にあります。
  )
) else (
  where git >nul 2>&1
  if errorlevel 1 (
    echo Git が入っていません。https://git-scm.com/download/win
    echo または GitHub から ZIP をダウンロードして、展開したフォルダでこのバッチを実行してください。
    pause
    exit /b 1
  )
  if exist "%DEST%\.git" (
    echo すでにクローン済みです。最新を取り込みます。
    git -C "%DEST%" pull
  ) else (
    echo GitHub からクローンします。
    git clone "%REPO_URL%" "%DEST%"
    if errorlevel 1 (
      echo クローンに失敗しました。
      pause
      exit /b 1
    )
  )
)

cd /d "%DEST%"
call "%DEST%\scripts\setup_env.bat"
if errorlevel 1 (
  pause
  exit /b 1
)

echo.
echo 次は「03_業務画面を起動.bat」を実行してください。
echo 場所: %DEST%
pause
endlocal
exit /b 0
