<?php
require __DIR__ . '/common.php';

$plan = trim((string)($_POST['myasp_plan_key'] ?? ''));
$subject = trim((string)($_POST['subject'] ?? ''));
$body = trim((string)($_POST['body'] ?? ''));
$notes = trim((string)($_POST['notes'] ?? ''));

if ($plan === '' || $subject === '' || $body === '') {
    http_response_code(400);
    echo 'プラン、件名、本文は必須です。';
    exit;
}
if (!in_array($plan, ['test_plan', 'production_plan'], true)) {
    http_response_code(400);
    echo 'プランの指定が正しくありません。';
    exit;
}

function intake_store_upload(array $file, string $prefix): ?array
{
    if (($file['error'] ?? UPLOAD_ERR_NO_FILE) === UPLOAD_ERR_NO_FILE) {
        return null;
    }
    if (($file['error'] ?? UPLOAD_ERR_OK) !== UPLOAD_ERR_OK) {
        return null;
    }
    $name = basename((string)$file['name']);
    $tmp = (string)$file['tmp_name'];
    if ($tmp === '' || !is_uploaded_file($tmp)) {
        return null;
    }
    $stored = intake_data_dir() . '/files/' . $prefix . '_' . bin2hex(random_bytes(4)) . '_' . preg_replace('/[^A-Za-z0-9._-]/', '_', $name);
    if (!move_uploaded_file($tmp, $stored)) {
        return null;
    }
    return [
        'filename' => $name,
        'path' => $stored,
    ];
}

$id = date('YmdHis') . '-' . bin2hex(random_bytes(3));
$record = [
    'id' => $id,
    'created_at' => gmdate('c'),
    'myasp_plan_key' => $plan,
    'subject' => $subject,
    'body' => $body,
    'notes' => $notes,
    'material' => intake_store_upload($_FILES['material'] ?? [], 'material'),
    'additions_csv' => intake_store_upload($_FILES['additions_csv'] ?? [], 'add'),
    'exclusions_csv' => intake_store_upload($_FILES['exclusions_csv'] ?? [], 'exclude'),
];

$pending = intake_data_dir() . '/pending/' . $id . '.json';
file_put_contents($pending, json_encode($record, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
?>
<!doctype html>
<html lang="ja">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>依頼を受け付けました</title>
  <style>
    body { font-family: "Yu Gothic UI", "Hiragino Sans", sans-serif; margin: 0; background: #f4f1ea; }
    main { max-width: 640px; margin: 48px auto; background: #fff; padding: 28px; border-radius: 12px; }
  </style>
</head>
<body>
  <main>
    <h1>依頼を受け付けました</h1>
    <p>担当者へ届きました。受付番号は <?php echo htmlspecialchars($id, ENT_QUOTES, 'UTF-8'); ?> です。</p>
    <p>この画面から配信は行われません。</p>
    <p><a href="index.php">別の依頼を送る</a></p>
  </main>
</body>
</html>
