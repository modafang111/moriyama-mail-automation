<?php
require __DIR__ . '/common.php';
?>
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>メルマガ配信依頼</title>
  <style>
    body { font-family: "Yu Gothic UI", "Hiragino Sans", sans-serif; margin: 0; background: #f4f1ea; color: #222; }
    main { max-width: 720px; margin: 32px auto; background: #fff; padding: 28px; border-radius: 12px; box-shadow: 0 8px 24px rgba(0,0,0,.08); }
    h1 { font-size: 22px; margin: 0 0 8px; }
    p.note { color: #555; line-height: 1.6; }
    label { display: block; margin: 16px 0 6px; font-weight: 600; }
    input[type=text], textarea, input[type=file] { width: 100%; box-sizing: border-box; padding: 10px; border: 1px solid #ccc; border-radius: 8px; }
    textarea { min-height: 180px; }
    textarea.signature { min-height: 140px; }
    .plans { display: flex; gap: 16px; flex-wrap: wrap; }
    pre.preview { background: #f7f4ee; padding: 12px; border-radius: 8px; white-space: pre-wrap; min-height: 160px; font-family: inherit; font-size: 14px; line-height: 1.6; }
    button { margin-top: 20px; background: #1f4e79; color: #fff; border: 0; padding: 12px 20px; border-radius: 8px; font-size: 16px; cursor: pointer; }
  </style>
</head>
<body>
  <main>
    <h1>メルマガ配信の依頼</h1>
    <p class="note">この画面は担当者への依頼窓口です。送る前に宛先ファイルなどを確認します。ここから読者への配信は行いません。</p>
    <form method="post" action="submit.php" enctype="multipart/form-data">
      <label>MyASPプラン（必須）</label>
      <div class="plans">
        <label><input type="radio" name="myasp_plan_key" value="test_plan" required checked> テストプラン</label>
        <label><input type="radio" name="myasp_plan_key" value="production_plan" required> 本番プラン</label>
      </div>
      <label>メール件名</label>
      <input type="text" name="subject" required>
      <label>メール本文</label>
      <textarea name="body" id="body" required></textarea>
      <p class="note">本文だけ書いてください。署名は次の欄で編集できます。</p>
      <label>署名</label>
      <textarea name="signature" id="signature" class="signature"><?php echo htmlspecialchars(intake_signature(), ENT_QUOTES, 'UTF-8'); ?></textarea>
      <p class="note">直した署名は、次に開いたときもこの内容が入ります。</p>
      <label>プレビュー（読者へ届く形・共有URL入り）</label>
      <pre class="preview" id="preview"></pre>
      <label>備考</label>
      <input type="text" name="notes">
      <label>配信用資料（必須。読者がドライブで見るファイル）</label>
      <input type="file" name="material" required>
      <label>宛先のファイル（必須・CSV）</label>
      <input type="file" name="additions_csv" accept=".csv" required>
      <p class="note">宛先ファイルはCSV（.csv）だけです。MyASPからダウンロードしたユーザーリストを、追加や修正したうえで付けてください。</p>
      <button type="submit">送信</button>
    </form>
    <script>
    (function () {
      var body = document.getElementById('body');
      var signatureBox = document.getElementById('signature');
      var preview = document.getElementById('preview');
      var label = '買取案件紹介';
      var placeholder = '{{DRIVE_SHARE_URL}}';
      function assemble(text, signature) {
        var mid = (text || '').replace(/\s+$/, '');
        var sig = (signature || '').replace(/^\s+|\s+$/g, '');
        if (mid.indexOf(placeholder) === -1) {
          mid = (mid ? mid + '\n\n' : '') + label + ': ' + placeholder;
        }
        if (sig) {
          return mid + '\n\n' + sig + '\n';
        }
        return mid;
      }
      function refresh() {
        preview.textContent = assemble(body.value, signatureBox.value);
      }
      body.addEventListener('input', refresh);
      signatureBox.addEventListener('input', refresh);
      refresh();
    })();
    </script>
  </main>
</body>
</html>
