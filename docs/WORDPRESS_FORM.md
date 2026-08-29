# WordPress-123.com への専用フォーム配置

顧客向けの専用フォームは **https://wordpress-123.com/mail-request/** に置きます。通知メールはこのプログラムからは送りません。

リモートデスクトップではコマンドプロンプトへ貼らなくて構いません。エクスプローラーとサーバーのファイルマネージャで進めます。

## サーバーへ置くもの

リポジトリの `web/wordpress-form` フォルダ一式です。

Xserver などのファイルマネージャで、サイトの公開フォルダ（多くの場合 `public_html`）に `mail-request` フォルダを作り、中身をアップロードします。

置くファイル:

- `index.php`
- `submit.php`
- `fetch.php`
- `common.php`
- `.htaccess`
- `config.example.php`
- `data/.htaccess`

## トークン

1. サーバー上で `config.example.php` を `config.php` にコピーする
2. `INTAKE_TOKEN` を自分だけが知る文字列に変える
3. 担当者PCの `.env` に同じ値を書く

```text
WORDPRESS_FORM_URL=https://wordpress-123.com/mail-request/
WORDPRESS_INTAKE_TOKEN=（config.php と同じ）
```

## 顧客の使い方

ブラウザで次を開きます。

https://wordpress-123.com/mail-request/

## 担当者の使い方

1. 担当者画面を開く
2. 「WordPressの依頼を取り込む」を押す
3. 案件一覧に入る
4. そのあと Drive・宛先・テスト／本番確認は [操作手順.md](操作手順.md) どおり

パスを `mail-request` 以外にする場合は、`.env` の `WORDPRESS_FORM_URL` も合わせて変えます。
