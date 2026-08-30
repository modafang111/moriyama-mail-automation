<?php
require __DIR__ . '/common.php';

$t_request = isset($_SERVER['REQUEST_TIME_FLOAT']) ? (float)$_SERVER['REQUEST_TIME_FLOAT'] : microtime(true);
$t_script = microtime(true);
$id = date('YmdHis') . '-' . bin2hex(random_bytes(3));
$steps = [];

$plan = trim((string)($_POST['myasp_plan_key'] ?? ''));
$subject = trim((string)($_POST['subject'] ?? ''));
$body = trim((string)($_POST['body'] ?? ''));
$notes = trim((string)($_POST['notes'] ?? ''));
$signature = trim((string)($_POST['signature'] ?? ''));
$material_size = (int)($_FILES['material']['size'] ?? 0);
$csv_size = (int)($_FILES['additions_csv']['size'] ?? 0);
intake_step($steps, $id, 'receive_upload', $t_request, [
    'material_bytes' => $material_size,
    'csv_bytes' => $csv_size,
]);

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

$t = microtime(true);
$material = intake_store_upload($_FILES['material'] ?? [], 'material');
$additions = intake_store_upload($_FILES['additions_csv'] ?? [], 'add');
intake_step($steps, $id, 'store_uploads', $t, [
    'material_ok' => is_array($material) ? '1' : '0',
    'csv_ok' => is_array($additions) ? '1' : '0',
]);
if (!is_array($material) || !is_array($additions)) {
    http_response_code(400);
    echo '配信用資料と宛先CSVは必須です。MyASP下書きの事前チェックに使います。';
    exit;
}
if (is_array($additions)) {
    $t = microtime(true);
    $format_errors = intake_check_myasp_userlist($additions['path'], (string)$additions['filename']);
    intake_step($steps, $id, 'csv_check', $t, [
        'csv_bytes' => $csv_size,
        'errors' => count($format_errors),
    ]);
    if ($format_errors) {
        if (!empty($material['path']) && is_file($material['path'])) {
            unlink($material['path']);
        }
        if (is_file($additions['path'])) {
            unlink($additions['path']);
        }
        http_response_code(400);
        header('Content-Type: text/html; charset=UTF-8');
        $data_error = false;
        foreach ($format_errors as $message) {
            if (strpos($message, '行目:') !== false) {
                $data_error = true;
                break;
            }
        }
        echo '<!doctype html><html lang="ja"><head><meta charset="utf-8"><title>このファイルは使えません</title>';
        echo '<style>body{font-family:"Yu Gothic UI","Hiragino Sans",sans-serif;margin:0;background:#f4f1ea;color:#222;}';
        echo 'main{max-width:640px;margin:48px auto;background:#fff;padding:28px;border-radius:12px;}';
        echo 'p,li{line-height:1.7;} .note{color:#555;}</style></head><body><main>';
        if ($data_error) {
            echo '<h1>ユーザーリストの内容に誤りがあります</h1>';
            echo '<p>次の理由を直してから、もう一度送ってください。</p>';
        } else {
            echo '<h1>このファイルは使えません</h1>';
            echo '<p>MyASPからダウンロードしたユーザーリストを、<strong>追加や修正したCSV</strong>を付けてください。</p>';
            echo '<p class="note">宛先ファイルはCSV（.csv）だけです。文字コードは UTF-8 または Shift_JIS です。</p>';
        }
        echo '<p>理由</p><ul>';
        foreach ($format_errors as $message) {
            echo '<li>' . htmlspecialchars($message, ENT_QUOTES, 'UTF-8') . '</li>';
        }
        echo '</ul><p><a href="index.php">戻って、別のファイルを付ける</a></p></main></body></html>';
        exit;
    }
}

$record = [
    'id' => $id,
    'created_at' => gmdate('c'),
    'myasp_plan_key' => $plan,
    'subject' => $subject,
    'body' => $body,
    'notes' => $notes,
    'signature' => $signature,
    'reader_body' => intake_assemble_reader_mail($body, '', $signature),
    'material' => $material,
    'additions_csv' => $additions,
];

$t = microtime(true);
$pending = intake_data_dir() . '/pending/' . $id . '.json';
file_put_contents($pending, json_encode($record, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
intake_save_signature($signature);
intake_step($steps, $id, 'save_pending', $t);
intake_step($steps, $id, 'submit_total', $t_script);

$html = '<!doctype html><html lang="ja"><head><meta charset="utf-8">';
$html .= '<meta name="viewport" content="width=device-width, initial-scale=1">';
$html .= '<title>依頼を受け付けました</title>';
$html .= '<style>body{font-family:"Yu Gothic UI","Hiragino Sans",sans-serif;margin:0;background:#f4f1ea;}';
$html .= 'main{max-width:640px;margin:48px auto;background:#fff;padding:28px;border-radius:12px;}</style>';
$html .= '</head><body><main>';
$html .= '<h1>依頼を受け付けました</h1>';
$html .= '<p>受付番号は ' . htmlspecialchars($id, ENT_QUOTES, 'UTF-8') . ' です。</p>';
$html .= '<p>担当者へ通知します。宛先ファイルなどは送信前に確認済みです。</p>';
$html .= '<p>ここから読者への配信は行いません。</p>';
$html .= '<p><a href="index.php">別の依頼を送る</a></p>';
$html .= '</main></body></html>';
intake_release_browser($html);

intake_load_config();
$notify = intake_notify_request($record);
$notified = !empty($notify['ok']);
if (!empty($notify['steps']) && is_array($notify['steps'])) {
    foreach ($notify['steps'] as $step) {
        $steps[] = $step;
    }
}
intake_log($id, 'notify_after_page', $t_script, ['notified' => $notified ? '1' : '0']);
$record['timing'] = $steps;
$record['notified'] = $notified;
file_put_contents($pending, json_encode($record, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
file_put_contents(
    intake_data_dir() . '/logs/' . $id . '.txt',
    intake_steps_text($steps) . "\n"
);
