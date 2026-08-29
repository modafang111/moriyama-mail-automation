# ローカルの Cursor で実行する

このフォルダを Cursor で開けば、このパソコン上で担当者画面とウェブ専用フォームを実行できます。通知メールはこのプログラムからは送りません。

## 1. フォルダを開く

Cursor でこのリポジトリのフォルダを開きます。例:

```text
D:\dev\moriyama-mail-automation
```

別の場所にクローンしていても、開いたフォルダが配置場所になります。

## 2. セットアップ

ターミナル（Ctrl+`）で:

```text
py -3 scripts/setup_local.py
```

`py` が無いときは:

```text
python scripts/setup_local.py
```

または、メニューの「ターミナル」→「タスクの実行」→「セットアップ」。

終わったら、コマンドパレット（Ctrl+Shift+P）で `Python: Select Interpreter` を選び、`.venv` の Python を指定します。

## 3. 実行

「実行とデバッグ」（Ctrl+Shift+D）から次を選び、開始（F5）します。

| 構成 | 内容 |
| --- | --- |
| 担当者画面 | 操作画面。同じパソコンでウェブフォームも起動します |
| ウェブ専用フォーム | フォームだけ（http://127.0.0.1:8787/ ） |
| pytest | テスト |

担当者画面を出したあと、左の「ウェブフォームを開く」でブラウザが開きます。

ターミナルからでも同じです。

```text
.venv\Scripts\python.exe -m moriyama_mail
```

フォームだけ:

```text
.venv\Scripts\python.exe -m moriyama_mail.intake.webapp
```

## うまく動かないとき

- Python 3.11 以上が入っているか
- インストール時に「Add python.exe to PATH」と Tcl/Tk（tkinter）が入っているか
- インタープリターが `.venv` になっているか
- `.env` があるか（セットアップが `.env.example` から作ります）
