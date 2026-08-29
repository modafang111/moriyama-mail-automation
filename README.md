# moriyama-mail-automation

顧客向けメルマガ配信業務を半自動化する、Windows用の業務支援プログラムです。

第1段階では、案件管理・本文作成・Googleドライブ連携・配信対象データの読み込み口・テスト／本番の安全確認・履歴保存までを実装しています。MyASPへの実配信は調査結果に基づくモックです。

## ローカルPCでの配置場所

推奨配置:

```text
D:\dev\moriyama-mail-automation
```

## 起動方法（Windows）

1. このリポジトリを `D:\dev\moriyama-mail-automation` にクローンする
2. `.env.example` を `.env` にコピーし、テスト配信先と通知先を記入する
3. `scripts\run_windows.bat` を実行する

手動で起動する場合:

```bat
cd /d D:\dev\moriyama-mail-automation
py -3 -m venv .venv
.venv\Scripts\python.exe -m pip install -r requirements.txt
.venv\Scripts\python.exe -m moriyama_mail
```

認証情報・顧客CSV・配信履歴データベースは GitHub に含まれません。`.gitignore` を参照してください。

## いまできること

- 専用フォームからの依頼受付（MyASPプランを2つから選択）
- 依頼登録時の通知メール（設定した宛先へ。1件目の例: modafang111@gmail.com）
- 件名・本文の登録
- 配信用資料の選択
- Googleドライブへのアップロードと閲覧専用共有URL取得（認証がある場合はAPI、ない場合はモック）
- 共有URLの本文への挿入
- 配信対象の追加、および「今回だけ送らない」除外の読み込み
- テスト配信 / 本番の予約配信の選択（初期値はテスト配信。即時の本番配信は使いません）
- 本番配信前の最終確認画面
- 本番配信済み案件の再配信防止
- 案件状態と進捗の表示
- 配信履歴の保存

MyASP実連携は次段階です。詳細は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) と [docs/MYASP_RESEARCH.md](docs/MYASP_RESEARCH.md) を参照してください。
