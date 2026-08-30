# moriyama-mail-automation

顧客向けメルマガ配信業務を半自動化する、Windows用の業務支援プログラムです。

依頼の通知は `D:\dev\cloud-agent-sync\notify.py` の `notify_note` です。パスワードはそちらの `notify.local.json` だけを使い、このプロジェクトの `.env` には書きません。配信用資料と追加する宛先のファイルを添付します。集計は入れません。

依頼は **ウェブの専用フォーム** です。配置先は [WordPress-123.com](https://wordpress-123.com/mail-request/) です。置き方は [docs/WORDPRESS_FORM.md](docs/WORDPRESS_FORM.md) です。

手で進める手順は [docs/操作手順.md](docs/操作手順.md) です。ローカルの Cursor で動かす手順は [docs/CURSOR.md](docs/CURSOR.md) です。

## ローカルの Cursor で実行

リモートデスクトップではコマンドプロンプトへ貼らなくて構いません。

1. このフォルダを Cursor で開く
2. 初回はエクスプローラーで `02_install.bat` をダブルクリック（またはメニュー「ターミナル」→「タスクの実行」→「セットアップ」）
3. `Python: Select Interpreter` で `.venv` を選ぶ
4. 「実行とデバッグ」から **担当者画面** を F5 で開始

コマンドを貼らずに動かすだけなら、`03_start.bat` をダブルクリックでも同じです。

詳しくは [docs/CURSOR.md](docs/CURSOR.md) です。

## ローカルPCへの置き方

配置場所:

```text
D:\dev\moriyama-mail-automation
```

パソコンにフォルダがまだ無い場合:

1. このリポジトリを ZIP でダウンロードして展開する
2. `01_setup.bat` を実行する（`01_フォルダを作って配置.bat` でも同じ）
3. `03_start.bat` を実行する

バッチの中身は英数字だけです。日本語Windowsのコマンドプロンプトが UTF-8 の `.bat` を壊すためです。

| バッチ | 役割 |
| --- | --- |
| `01_setup.bat` | `D:\dev` 作成、配置、初回セットアップ |
| `02_install.bat` | 配置済みのとき、部品の入れ直し |
| `03_start.bat` | 担当者の操作画面 |
| `deploy_wordpress_form.bat` | WordPress-123.com へ専用フォームを配置（`04_WordPressフォームを配置.bat` でも同じ） |
| `open_web_form.bat` | WordPress-123.com の専用フォームを開く |

詳しくは [docs/LOCAL_SETUP.md](docs/LOCAL_SETUP.md) を見てください。

## いまできること

- ウェブの専用依頼フォーム（https://wordpress-123.com/mail-request/ ）
- WordPressからの依頼取り込み（担当者画面）
- 手作業の操作手順（[docs/操作手順.md](docs/操作手順.md)）
- 件名・本文の登録
- 配信用資料の選択
- Googleドライブへのアップロードと閲覧専用共有URL取得（認証がある場合はAPI、ない場合はモック）
- 共有URLの本文への挿入
- 配信対象の追加（送らない宛先は追加ファイルを直してから送る）
- テスト配信 / 本番の予約配信の選択（初期値はテスト配信。即時の本番配信は使いません）
- 本番配信前の最終確認画面
- 本番配信済み案件の再配信防止
- 案件状態と進捗の表示
- 配信履歴の保存

MyASP実連携は次段階です。詳細は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照してください。
