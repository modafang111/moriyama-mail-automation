# WordPress-123.com への専用フォーム配置

顧客向けの専用フォームは **https://wordpress-123.com/mail-request/** に置きます。通知メールはこのプログラムからは送りません。

リモートデスクトップではコマンドプロンプトへ貼らなくて構いません。

## ローカル Cursor / バッチで配置する

1. `.env` に次を書く（サーバーの FTP 情報。パスワードは Git に載せない）

```text
WORDPRESS_FORM_URL=https://wordpress-123.com/mail-request/
WORDPRESS_INTAKE_TOKEN=自分だけが知る文字列
WORDPRESS_FTP_HOST=（Xserver の FTP ホスト）
WORDPRESS_FTP_USER=（FTP ユーザー）
WORDPRESS_FTP_PASSWORD=（FTP パスワード）
WORDPRESS_FTP_REMOTE_DIR=public_html/mail-request
WORDPRESS_FTP_TLS=1
```

Xserver では FTP ホストが `svXXXX.xserver.jp` のことがあります。ログイン直後の場所が公開フォルダなら `WORDPRESS_FTP_REMOTE_DIR=mail-request` にします。

2. 配置を実行する（どれか一つ）

- エクスプローラーで `deploy_wordpress_form.bat` をダブルクリック（`04_WordPressフォームを配置.bat` でも同じ）
- Cursor のメニュー「ターミナル」→「タスクの実行」→「WordPressフォームを配置」

バッチが `web/wordpress-form` をサーバーへ送り、`.env` のトークンで `config.php` を作ります。依頼データ（pending）は上書きしません。

3. ブラウザで https://wordpress-123.com/mail-request/ を開いて確認する

## 担当者の使い方

1. 担当者画面を開く
2. 「WordPressの依頼を取り込む」を押す
3. 案件一覧に入る
4. そのあと Drive・宛先・テスト／本番確認は [操作手順.md](操作手順.md) どおり

`.env` の `WORDPRESS_INTAKE_TOKEN` は、サーバーの `config.php` と同じ値です。配置バッチが両方に揃えます。
