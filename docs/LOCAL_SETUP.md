# ローカルPCへの配置

パソコンに `D:\dev` もプログラムも無い状態から始められます。通知メールはこのプログラムからは送りません。

バッチファイルの中身は **英数字だけ** にしてあります。日本語Windowsのコマンドプロンプトは UTF-8 の `.bat` を読めず、文字化けして途中で壊れます。画面の日本語はプログラム側に残しています。

英数字の名前でも同じ処理です。

- `01_setup.bat` = `01_フォルダを作って配置.bat`
- `02_install.bat` = `02_初回セットアップ.bat`
- `03_start.bat` = `03_業務画面を起動.bat`
- `04_start_form.bat` = `04_顧客向けフォームを起動.bat`

## 用意するもの

- Windows
- Python 3.11 以上（インストール時に「Add python.exe to PATH」にチェック）
- 可能なら Git（無くても ZIP で進められます）

Python の入手先: https://www.python.org/downloads/

## 手順（フォルダがまだ無いとき）

1. GitHub のこのリポジトリから **Code → Download ZIP** でダウンロードする
2. ZIP を適当な場所（ダウンロードフォルダなど）へ展開する
3. 展開したフォルダの `01_setup.bat`（または `01_フォルダを作って配置.bat`）をダブルクリックする

このバッチが次を行います。

- `D:\dev` を作る
- プログラムを `D:\dev\moriyama-mail-automation` へコピーする
- 仮想環境を作って必要な部品を入れる
- `.env.example` から `.env` を作る

終わったら、配置先のフォルダで次を実行します。

- `03_start.bat` … 担当者の操作画面
- `04_start_form.bat` … 顧客がブラウザで開く依頼画面（http://127.0.0.1:8787/）

Git が入っている場合は、ZIP の代わりに次でも同じです。

```text
git clone https://github.com/modafang111/moriyama-mail-automation.git D:\dev\moriyama-mail-automation
```

そのあと `02_install.bat` を実行します。

## バッチの役割

| ファイル | 役割 |
| --- | --- |
| `01_setup.bat` | `D:\dev` 作成、配置、初回セットアップ |
| `02_install.bat` | すでに配置済みのとき、部品の入れ直し |
| `03_start.bat` | 担当者画面を開く |
| `04_start_form.bat` | 顧客向けフォームを開く |

## 次にやること

まずはモックのまま、依頼登録と画面操作を確認します。Googleドライブの実アップロードや MyASP 実連携は、プログラムが手元で動いてから進めます。通知メールは共通の通知処理ができてからつなぎます。
