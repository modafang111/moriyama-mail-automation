# ローカルPCへの配置

パソコンに `D:\dev` もプログラムも無い状態から始められます。通知メールはこのプログラムからは送りません。

依頼は WordPress-123.com 上のウェブ専用フォームです。開き方と手作業の順番は [操作手順.md](操作手順.md)、サーバーへの置き方は [WORDPRESS_FORM.md](WORDPRESS_FORM.md) です。ローカルの Cursor で開いて実行する手順は [CURSOR.md](CURSOR.md) です。

バッチファイルの中身は **英数字だけ** にしてあります。日本語Windowsのコマンドプロンプトは UTF-8 の `.bat` を読めず、文字化けして途中で壊れます。画面の日本語はプログラム側に残しています。

英数字の名前でも同じ処理です。

- `01_setup.bat` = `01_フォルダを作って配置.bat`
- `02_install.bat` = `02_初回セットアップ.bat`
- `03_start.bat` = `03_業務画面を起動.bat`
- `deploy_wordpress_form.bat` = `04_WordPressフォームを配置.bat`

ウェブの専用フォームは https://wordpress-123.com/mail-request/ です。`open_web_form.bat` はそのページを開きます。

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

終わったら、配置先のフォルダで `03_start.bat` を実行して担当者画面を開きます。依頼フォームは画面の「ウェブフォームを開く」か `open_web_form.bat` です。手作業の順番は [操作手順.md](操作手順.md) です。

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
| `deploy_wordpress_form.bat` | WordPress-123.com へ専用フォームを配置（`04_WordPressフォームを配置.bat` でも同じ） |
| `open_web_form.bat` | WordPress-123.com の専用フォームを開く |

## 次にやること

まずは [操作手順.md](操作手順.md) どおり、モックのまま手で操作を確認します。Googleドライブの実アップロードや MyASP 実連携は、そのあとです。
