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
    .plans { display: flex; gap: 16px; flex-wrap: wrap; }
    button { margin-top: 20px; background: #1f4e79; color: #fff; border: 0; padding: 12px 20px; border-radius: 8px; font-size: 16px; cursor: pointer; }
  </style>
</head>
<body>
  <main>
    <h1>メルマガ配信の依頼</h1>
    <p class="note">WordPress-123.com 上の専用依頼フォームです。送信すると担当者へ届きます。この画面から配信は行われません。</p>
    <form method="post" action="submit.php" enctype="multipart/form-data">
      <label>MyASPプラン（必須）</label>
      <div class="plans">
        <label><input type="radio" name="myasp_plan_key" value="test_plan" required> テストプラン</label>
        <label><input type="radio" name="myasp_plan_key" value="production_plan" required> 本番プラン</label>
      </div>
      <label>メール件名</label>
      <input type="text" name="subject" required>
      <label>メール本文</label>
      <textarea name="body" required></textarea>
      <label>備考</label>
      <input type="text" name="notes">
      <label>配信用資料（PDFなど）</label>
      <input type="file" name="material">
      <label>追加する宛先のファイル</label>
      <input type="file" name="additions_csv" accept=".csv,.txt">
      <label>今回だけ送らない宛先のファイル</label>
      <input type="file" name="exclusions_csv" accept=".csv,.txt">
      <p class="note">「今回だけ送らない」は、その配信のときだけ送らない指定です。リストから名前は消しません。</p>
      <button type="submit">担当者へ依頼を送る</button>
    </form>
  </main>
</body>
</html>
