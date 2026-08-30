# 未確定事項

決まっていない項目だけ残しています。推測で埋めていません。

## いま確定したこと

- 除外: その配信のときだけ送らない
- 依頼: ウェブの専用フォーム。配置先は WordPress-123.com（`https://wordpress-123.com/mail-request/`）
- MyASPプランの仮置き: テストプラン / 本番プラン
- 本番の即時配信は今は不要（予約配信）
- 「削除」は最初の仕様文に書いてあった言葉ですが、業務上の操作としては使わない
- 依頼受付の通知は `D:\dev\cloud-agent-sync\notify.py` の `notify_note` で送る。資料は添付。集計は入れない

## まだ決めていないこと

- テスト配信の宛先（`.env` の `TEST_RECIPIENTS`。未設定のあいだはテスト配信を実行できない）
- 2つのプランの正式名称（今は仮置き）とシナリオID
- 追加宛先CSVの列名（MyASPユーザーリストの書式チェックは `check_myasp_userlist`）
- GoogleドライブのフォルダID

SMTPと宛先は `D:\dev\cloud-agent-sync\notify.local.json` だけを使います。このプログラムの `.env` には載せません。

手作業の順番は `docs/操作手順.md` です。WordPressへの置き方は `docs/WORDPRESS_FORM.md` です。
