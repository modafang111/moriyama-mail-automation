<?php

function intake_config_path(): string
{
    return __DIR__ . '/config.php';
}

function intake_load_config(bool $require_real_token = false): void
{
    $path = intake_config_path();
    if (!is_file($path)) {
        http_response_code(500);
        echo 'config.php がありません。config.example.php をコピーしてトークンを入れてください。';
        exit;
    }
    require $path;
    if (!defined('INTAKE_TOKEN') || INTAKE_TOKEN === '') {
        http_response_code(500);
        echo 'INTAKE_TOKEN を設定してください。';
        exit;
    }
    if ($require_real_token && INTAKE_TOKEN === 'replace-this-intake-token') {
        http_response_code(500);
        echo 'INTAKE_TOKEN を本番用の値に変更してください。';
        exit;
    }
}

function intake_data_dir(): string
{
    $dir = __DIR__ . '/data';
    foreach (['pending', 'done', 'files', 'logs'] as $name) {
        $path = $dir . '/' . $name;
        if (!is_dir($path)) {
            mkdir($path, 0750, true);
        }
    }
    return $dir;
}

function intake_elapsed_ms(float $started): int
{
    return (int)round((microtime(true) - $started) * 1000);
}

function intake_format_ms(int $ms): string
{
    if ($ms < 1000) {
        return $ms . 'ms';
    }
    return number_format($ms / 1000, 1) . '秒';
}

function intake_format_bytes(int $n): string
{
    if ($n < 1024) {
        return $n . 'B';
    }
    if ($n < 1048576) {
        return number_format($n / 1024, 1) . 'KB';
    }
    return number_format($n / 1048576, 1) . 'MB';
}

function intake_step_label(string $name): string
{
    $labels = [
        'receive_upload' => 'ファイル受信',
        'store_uploads' => 'ファイル保存',
        'csv_check' => 'CSV検査',
        'save_pending' => '依頼の保存',
        'notify_build_mime' => '通知メール作成',
        'notify_smtp_connect' => 'SMTP接続',
        'notify_smtp_starttls' => 'SMTP暗号化',
        'notify_smtp_auth' => 'SMTP認証',
        'notify_smtp_data' => 'SMTP送信',
        'notify_total' => '通知メール全体',
        'notify_fail' => '通知失敗',
        'submit_total' => '受付全体',
    ];
    return isset($labels[$name]) ? $labels[$name] : $name;
}

function intake_log_line(string $id, string $step, int $ms, array $extra = []): string
{
    $parts = [gmdate('c'), $id, $step, $ms . 'ms'];
    foreach ($extra as $key => $value) {
        $safe = str_replace(["\t", "\r", "\n"], ' ', (string)$value);
        $parts[] = $key . '=' . $safe;
    }
    return implode("\t", $parts);
}

function intake_write_log(string $line): void
{
    $path = intake_data_dir() . '/logs/' . gmdate('Ymd') . '.log';
    file_put_contents($path, $line . "\n", FILE_APPEND | LOCK_EX);
}

function intake_log(string $id, string $step, float $started, array $extra = []): int
{
    $ms = intake_elapsed_ms($started);
    intake_write_log(intake_log_line($id, $step, $ms, $extra));
    return $ms;
}

function intake_step(array &$steps, string $id, string $name, float $started, array $extra = []): int
{
    $ms = intake_log($id, $name, $started, $extra);
    $steps[] = ['name' => $name, 'ms' => $ms, 'extra' => $extra];
    return $ms;
}

function intake_format_extra(array $extra): string
{
    $bits = [];
    foreach ($extra as $key => $value) {
        $key = (string)$key;
        if ($key === 'bytes' || $key === 'written' || (strlen($key) > 6 && substr($key, -6) === '_bytes')) {
            $bits[] = $key . '=' . intake_format_bytes((int)$value);
        } else {
            $bits[] = $key . '=' . (string)$value;
        }
    }
    return implode(' ', $bits);
}

function intake_steps_text(array $steps): string
{
    $lines = [];
    foreach ($steps as $step) {
        $name = intake_step_label((string)($step['name'] ?? ''));
        $ms = (int)($step['ms'] ?? 0);
        $extra = is_array($step['extra'] ?? null) ? intake_format_extra($step['extra']) : '';
        $lines[] = $name . ': ' . intake_format_ms($ms) . ($extra !== '' ? '  ' . $extra : '');
    }
    return implode("\n", $lines);
}

function intake_steps_html(array $steps): string
{
    $html = '<h2>処理時間</h2>';
    $html .= '<p class="note">サーバー側の内訳です。通知メールの送信はこの画面のあとで続け、同じログファイルに追記します。</p>';
    $html .= '<table class="timing"><thead><tr><th>処理</th><th>時間</th><th>詳細</th></tr></thead><tbody>';
    foreach ($steps as $step) {
        $name = htmlspecialchars(intake_step_label((string)($step['name'] ?? '')), ENT_QUOTES, 'UTF-8');
        $ms = htmlspecialchars(intake_format_ms((int)($step['ms'] ?? 0)), ENT_QUOTES, 'UTF-8');
        $extra = is_array($step['extra'] ?? null) ? htmlspecialchars(intake_format_extra($step['extra']), ENT_QUOTES, 'UTF-8') : '';
        $html .= '<tr><td>' . $name . '</td><td>' . $ms . '</td><td>' . $extra . '</td></tr>';
    }
    $html .= '</tbody></table>';
    return $html;
}

function intake_json_header(): void
{
    header('Content-Type: application/json; charset=utf-8');
    header('Cache-Control: no-store, no-cache, must-revalidate');
    header('Pragma: no-cache');
}

function intake_token_ok(string $token): bool
{
    return hash_equals(INTAKE_TOKEN, $token);
}

function intake_smtp_read($fp): string
{
    $out = '';
    while (($line = fgets($fp, 4096)) !== false) {
        $out .= $line;
        if (preg_match('/^\d{3} /', $line)) {
            break;
        }
    }
    return $out;
}

function intake_smtp_cmd($fp, string $line): string
{
    fwrite($fp, $line . "\r\n");
    return intake_smtp_read($fp);
}

function intake_drive_placeholder(): string
{
    return '{{DRIVE_SHARE_URL}}';
}

function intake_apply_share_url(string $body, string $url, string $link_label = '買取案件紹介'): string
{
    $share = trim($url);
    if ($share === '') {
        return $body;
    }
    $placeholder = intake_drive_placeholder();
    if (strpos($body, $placeholder) !== false) {
        return str_replace($placeholder, $share, $body);
    }
    if (strpos($body, $share) !== false) {
        return $body;
    }
    $line = trim($link_label) !== '' ? trim($link_label) . ': ' . $share : $share;
    if (trim($body) !== '') {
        return rtrim($body) . "\n\n" . $line . "\n";
    }
    return $line . "\n";
}

function intake_signature(): string
{
    $saved = intake_data_dir() . '/signature.txt';
    if (is_file($saved)) {
        return trim((string)file_get_contents($saved));
    }
    $path = __DIR__ . '/signature.txt';
    if (!is_file($path)) {
        return '';
    }
    return trim((string)file_get_contents($path));
}

function intake_save_signature(string $signature): void
{
    file_put_contents(intake_data_dir() . '/signature.txt', $signature);
}

function intake_assemble_signed_body(string $original, string $signature = ''): string
{
    $mid = rtrim($original);
    $sig = trim($signature);
    if ($mid !== '' && $sig !== '') {
        return $mid . "\n\n" . $sig . "\n";
    }
    if ($sig !== '') {
        return $sig . "\n";
    }
    return $mid !== '' ? $mid : '（なし）';
}

function intake_assemble_reader_mail(string $original, string $share_url = '', string $signature = ''): string
{
    $marker = trim($share_url) !== '' ? trim($share_url) : intake_drive_placeholder();
    $mid = rtrim(intake_apply_share_url($original, $marker));
    $sig = trim($signature);
    if ($mid !== '' && $sig !== '') {
        return $mid . "\n\n" . $sig . "\n";
    }
    if ($sig !== '') {
        return $sig . "\n";
    }
    return $mid !== '' ? $mid : '（なし）';
}

function intake_draft_reader_body(string $original, string $share_url = ''): string
{
    return intake_assemble_reader_mail($original, $share_url);
}

function intake_notice_text(array $record): array
{
    $plan = (string)($record['myasp_plan_key'] ?? '');
    $plan_label = $plan === 'production_plan' ? '本番プラン' : ($plan === 'test_plan' ? 'テストプラン' : $plan);
    $has_material = is_array($record['material'] ?? null);
    $has_additions = is_array($record['additions_csv'] ?? null);
    $original = trim((string)($record['body'] ?? ''));
    $share_url = trim((string)($record['drive_share_url'] ?? ''));
    $signature = (string)($record['signature'] ?? '');
    $before = intake_assemble_signed_body($original, $signature);
    $drafted = intake_assemble_reader_mail($original, $share_url, $signature);
    $url_line = $share_url !== '' ? $share_url : 'まだ（次の工程でDriveへ上げたあと入ります）';
    $subject = '[メルマガ依頼] ' . ((string)($record['subject'] ?? '') ?: (string)($record['id'] ?? '新規依頼'));
    $rule = '------------------------------------------------------------';
    $body = implode("\n", [
        'メルマガ配信の依頼が届きました。',
        '宛先ファイルの書式は送信前に確認しています。ここから読者へは送っていません。',
        '',
        $rule,
        '■ 依頼の内容',
        $rule,
        '受付番号　' . (string)($record['id'] ?? ''),
        '件名　　　' . (string)($record['subject'] ?? ''),
        'プラン　　' . $plan_label,
        '受付日時　' . (string)($record['created_at'] ?? ''),
        '備考　　　' . (((string)($record['notes'] ?? '') !== '') ? (string)$record['notes'] : 'なし'),
        '',
        $rule,
        '■ 1. 盛山さんが書いた本文（修正前）',
        '本文に署名を付けた形です。共有URLはまだ入っていません。',
        $rule,
        $before,
        '',
        $rule,
        '■ 2. 読者へ送る本文（修正後）',
        '上の本文に、共有URLの位置と署名を付けた形です。',
        '共有URL　' . $url_line,
        $rule,
        $drafted,
        '',
        $rule,
        '■ 添付ファイル',
        $rule,
        '配信用資料　　　　' . ($has_material ? 'このメールに添付しています。' : 'ありません。'),
        '宛先のファイル　　' . ($has_additions ? 'このメールに添付しています。' : 'ありません。'),
        'フォーム　https://wordpress-123.com/mail-request/',
    ]);
    return [$subject, $body];
}

function intake_collect_files(array $record): array
{
    $files = [];
    foreach (['material' => 'shiryo', 'additions_csv' => 'atesaki'] as $key => $kind) {
        $info = $record[$key] ?? null;
        if (!is_array($info) || empty($info['path']) || !is_file($info['path'])) {
            continue;
        }
        $name = $kind . '_' . preg_replace('/[^A-Za-z0-9._-]/', '_', basename((string)($info['filename'] ?? $kind)));
        $files[] = [
            'filename' => $name,
            'bytes' => (string)file_get_contents($info['path']),
        ];
    }
    return $files;
}

function intake_release_browser(string $html): void
{
    ignore_user_abort(true);
    set_time_limit(180);
    header('Content-Type: text/html; charset=UTF-8');
    header('Content-Length: ' . strlen($html));
    header('Connection: close');
    echo $html;
    if (function_exists('fastcgi_finish_request')) {
        fastcgi_finish_request();
        return;
    }
    while (ob_get_level() > 0) {
        ob_end_flush();
    }
    flush();
}

function intake_build_mime(string $from, string $to, string $subject, string $body, array $files): string
{
    $boundary = 'bnd_' . bin2hex(random_bytes(8));
    $encoded = '=?UTF-8?B?' . base64_encode($subject) . '?=';
    $msg = 'From: ' . $from . "\r\n";
    $msg .= 'To: ' . $to . "\r\n";
    $msg .= 'Subject: ' . $encoded . "\r\n";
    $msg .= "MIME-Version: 1.0\r\n";
    $msg .= 'Content-Type: multipart/mixed; boundary="' . $boundary . '"' . "\r\n\r\n";
    $msg .= '--' . $boundary . "\r\n";
    $msg .= "Content-Type: text/plain; charset=UTF-8\r\n";
    $msg .= "Content-Transfer-Encoding: base64\r\n\r\n";
    $msg .= chunk_split(base64_encode($body));
    foreach ($files as $file) {
        $fname = str_replace(['"', "\r", "\n"], '', (string)$file['filename']);
        $msg .= '--' . $boundary . "\r\n";
        $msg .= 'Content-Type: application/octet-stream; name="' . $fname . '"' . "\r\n";
        $msg .= "Content-Transfer-Encoding: base64\r\n";
        $msg .= 'Content-Disposition: attachment; filename="' . $fname . '"' . "\r\n\r\n";
        $msg .= chunk_split(base64_encode((string)$file['bytes']));
    }
    $msg .= '--' . $boundary . "--\r\n";
    return $msg;
}

function intake_notify_fail(string $id, array $steps, float $started, string $reason): array
{
    intake_step($steps, $id, 'notify_fail', $started, ['reason' => $reason]);
    return ['ok' => false, 'steps' => $steps, 'reason' => $reason];
}

function intake_notify_request(array $record): array
{
    $id = (string)($record['id'] ?? '-');
    $steps = [];
    $t_all = microtime(true);
    if (!defined('NOTIFY_TO') || NOTIFY_TO === '' || !defined('NOTIFY_SMTP_HOST') || NOTIFY_SMTP_HOST === '') {
        return intake_notify_fail($id, $steps, $t_all, 'config');
    }
    $from = defined('NOTIFY_FROM') ? NOTIFY_FROM : '';
    $password = defined('NOTIFY_PASSWORD') ? NOTIFY_PASSWORD : '';
    $to = NOTIFY_TO;
    $host = NOTIFY_SMTP_HOST;
    $port = defined('NOTIFY_SMTP_PORT') ? (int)NOTIFY_SMTP_PORT : 587;
    if ($from === '' || $password === '') {
        return intake_notify_fail($id, $steps, $t_all, 'auth_config');
    }

    $t = microtime(true);
    $files = intake_collect_files($record);
    $file_sizes = [];
    $attach_bytes = 0;
    foreach ($files as $file) {
        $size = strlen((string)$file['bytes']);
        $attach_bytes += $size;
        $file_sizes[] = (string)$file['filename'] . ':' . $size;
    }
    [$subject, $body] = intake_notice_text($record);
    $mime = intake_build_mime($from, $to, $subject, $body, $files);
    intake_step($steps, $id, 'notify_build_mime', $t, [
        'mime_bytes' => strlen($mime),
        'attach_bytes' => $attach_bytes,
        'files' => implode(',', $file_sizes),
    ]);

    $errno = 0;
    $errstr = '';
    $t = microtime(true);
    $fp = @stream_socket_client('tcp://' . $host . ':' . $port, $errno, $errstr, 20);
    intake_step($steps, $id, 'notify_smtp_connect', $t, [
        'ok' => $fp !== false ? '1' : '0',
        'errno' => $errno,
    ]);
    if ($fp === false) {
        return intake_notify_fail($id, $steps, $t_all, 'connect');
    }
    stream_set_timeout($fp, 20);
    intake_smtp_read($fp);
    intake_smtp_cmd($fp, 'EHLO mail-request');
    $t = microtime(true);
    $starttls = intake_smtp_cmd($fp, 'STARTTLS');
    $tls_ok = preg_match('/^220/', $starttls) && @stream_socket_enable_crypto($fp, true, STREAM_CRYPTO_METHOD_TLS_CLIENT);
    intake_step($steps, $id, 'notify_smtp_starttls', $t, ['ok' => $tls_ok ? '1' : '0']);
    if (!$tls_ok) {
        fclose($fp);
        return intake_notify_fail($id, $steps, $t_all, 'starttls');
    }
    intake_smtp_cmd($fp, 'EHLO mail-request');
    $t = microtime(true);
    intake_smtp_cmd($fp, 'AUTH LOGIN');
    intake_smtp_cmd($fp, base64_encode($from));
    $auth = intake_smtp_cmd($fp, base64_encode($password));
    $auth_ok = (bool)preg_match('/^235/', $auth);
    intake_step($steps, $id, 'notify_smtp_auth', $t, ['ok' => $auth_ok ? '1' : '0']);
    if (!$auth_ok) {
        fclose($fp);
        return intake_notify_fail($id, $steps, $t_all, 'auth');
    }
    intake_smtp_cmd($fp, 'MAIL FROM:<' . $from . '>');
    $rcpt = intake_smtp_cmd($fp, 'RCPT TO:<' . $to . '>');
    if (!preg_match('/^250/', $rcpt)) {
        fclose($fp);
        return intake_notify_fail($id, $steps, $t_all, 'rcpt');
    }
    $data = intake_smtp_cmd($fp, 'DATA');
    if (!preg_match('/^354/', $data)) {
        fclose($fp);
        return intake_notify_fail($id, $steps, $t_all, 'data');
    }
    $payload = $mime . "\r\n.\r\n";
    $len = strlen($payload);
    $written = 0;
    $t = microtime(true);
    stream_set_timeout($fp, 90);
    while ($written < $len) {
        $chunk = fwrite($fp, substr($payload, $written));
        if ($chunk === false || $chunk === 0) {
            break;
        }
        $written += $chunk;
    }
    $done = intake_smtp_read($fp);
    $meta = stream_get_meta_data($fp);
    $timed_out = !empty($meta['timed_out']) ? '1' : '0';
    @intake_smtp_cmd($fp, 'QUIT');
    fclose($fp);
    $reply = preg_match('/^(\d{3})/m', $done, $m) ? $m[1] : 'none';
    $ok = !preg_match('/^[45]\d\d/m', $done) && (preg_match('/^250/m', $done) || $written === $len);
    intake_step($steps, $id, 'notify_smtp_data', $t, [
        'ok' => $ok ? '1' : '0',
        'written' => $written,
        'payload_bytes' => $len,
        'reply' => $reply,
        'timed_out' => $timed_out,
    ]);
    intake_step($steps, $id, 'notify_total', $t_all, ['ok' => $ok ? '1' : '0']);
    return ['ok' => $ok, 'steps' => $steps];
}

function intake_myasp_required_headers(): array
{
    return ['ユーザーID', '注文ID', 'メールアドレス', '配信可能/不可能', 'シナリオ名（購入商品）'];
}

function intake_is_csv_filename(string $filename): bool
{
    $name = strtolower(basename(str_replace('\\', '/', $filename)));
    $len = strlen($name);
    return $len >= 4 && substr($name, -4) === '.csv';
}

function intake_looks_like_excel(string $raw, string $filename = ''): bool
{
    $lower = strtolower($filename);
    $len = strlen($lower);
    if ($len >= 5 && substr($lower, -5) === '.xlsx') {
        return true;
    }
    if ($len >= 4 && substr($lower, -4) === '.xls') {
        return true;
    }
    return strncmp($raw, 'PK', 2) === 0;
}

function intake_strip_utf8_bom(string $text): string
{
    if (strncmp($text, "\xEF\xBB\xBF", 3) === 0) {
        return (string)substr($text, 3);
    }
    return $text;
}

function intake_decode_userlist(string $raw): array
{
    $raw = intake_strip_utf8_bom($raw);
    $probe = substr($raw, 0, 16384);
    if (strpos($probe, 'メールアドレス') !== false) {
        return [$raw, 'utf-8'];
    }
    foreach (['SJIS-win', 'CP932'] as $enc) {
        $probe_text = @mb_convert_encoding($probe, 'UTF-8', $enc);
        if (is_string($probe_text) && strpos($probe_text, 'メールアドレス') !== false) {
            $text = @mb_convert_encoding($raw, 'UTF-8', $enc);
            return [is_string($text) ? $text : $probe_text, 'cp932'];
        }
    }
    if (function_exists('mb_check_encoding') && @mb_check_encoding($raw, 'UTF-8')) {
        return [$raw, 'utf-8'];
    }
    $text = @mb_convert_encoding($raw, 'UTF-8', 'SJIS-win');
    return is_string($text) ? [$text, 'cp932'] : [null, ''];
}

function intake_row_is_empty(array $row): bool
{
    foreach ($row as $cell) {
        if (trim((string)$cell) !== '') {
            return false;
        }
    }
    return true;
}

function intake_drop_trailing_empty(array $rows): array
{
    while ($rows && intake_row_is_empty($rows[count($rows) - 1])) {
        array_pop($rows);
    }
    return $rows;
}

function intake_parse_csv_rows(string $text): array
{
    $fp = fopen('php://temp', 'r+');
    fwrite($fp, $text);
    rewind($fp);
    $rows = [];
    while (($row = fgetcsv($fp)) !== false) {
        $rows[] = $row;
    }
    fclose($fp);
    return $rows;
}

function intake_check_myasp_userlist(string $path, string $filename = ''): array
{
    $errors = [];
    if ($filename !== '' && !intake_is_csv_filename($filename)) {
        return ['宛先ファイルはCSV（.csv）だけ使えます。Excelやテキストのままでは送れません。'];
    }
    if (!is_file($path)) {
        return ['宛先ファイルがありません。'];
    }
    $raw = (string)file_get_contents($path);
    if ($raw === '') {
        return ['宛先ファイルが空です。'];
    }
    if (intake_looks_like_excel($raw, $filename)) {
        return ['Excelのままでは使えません。追加や修正したCSV（.csv）を付けてください。'];
    }
    list($text, $encoding) = intake_decode_userlist($raw);
    if ($text === null) {
        return [
            'CSVとして読めません。文字コードは UTF-8 または Shift_JIS（CP932）にしてください。',
            '追加や修正したCSVを付けてください。',
        ];
    }
    $rows = intake_parse_csv_rows($text);
    if ($rows === []) {
        return ['見出し行がありません。追加や修正したCSVを付けてください。'];
    }
    $headers = array_map(function ($cell) {
        return trim((string)$cell);
    }, $rows[0]);
    if ($headers && strncmp($headers[0], "\xEF\xBB\xBF", 3) === 0) {
        $headers[0] = (string)substr($headers[0], 3);
    }
    $header_count = count($headers);
    $index = array_flip($headers);
    $missing = [];
    foreach (intake_myasp_required_headers() as $name) {
        if (!isset($index[$name])) {
            $missing[] = $name;
        }
    }
    $data_rows = intake_drop_trailing_empty(array_slice($rows, 1));
    $stats = '（文字コード: ' . ($encoding !== '' ? $encoding : '不明') . '、見出しの列数: ' . $header_count . '、データ行数: ' . count($data_rows) . '）';
    if ($missing) {
        return [
            'このファイルは、MyASPのユーザーリストの形式ではありません。',
            '必要な列がありません: ' . implode('、', $missing),
            'メールアドレスだけを書いた一覧は使えません。',
            $stats,
        ];
    }
    if ($data_rows === []) {
        return ['データ行がありません。末尾の空行は除いています。', $stats];
    }
    $email_re = '/^[^@\s]+@[^@\s]+\.[^@\s]+$/i';
    $id_re = '/^[A-Za-z0-9_-]+$/';
    $allow = ['配信可能' => true, '配信不可能' => true];
    $seen = [];
    $max_errors = 40;
    foreach ($data_rows as $offset => $raw_row) {
        $row_no = $offset + 2;
        $actual = count($raw_row);
        if ($actual !== $header_count) {
            $errors[] = $row_no . '行目: 列数が見出し（' . $header_count . '列）と違います。この行は' . $actual . '列です。';
        }
        $user = trim((string)($raw_row[$index['ユーザーID']] ?? ''));
        $order = trim((string)($raw_row[$index['注文ID']] ?? ''));
        $email = trim((string)($raw_row[$index['メールアドレス']] ?? ''));
        $flag = trim((string)($raw_row[$index['配信可能/不可能']] ?? ''));
        if ($user === '') {
            $errors[] = $row_no . '行目: ユーザーIDが空です。';
        } elseif (!preg_match($id_re, $user)) {
            $errors[] = $row_no . '行目: ユーザーIDの形式が正しくありません。';
        }
        if ($order === '') {
            $errors[] = $row_no . '行目: 注文IDが空です。';
        } elseif (!preg_match($id_re, $order)) {
            $errors[] = $row_no . '行目: 注文IDの形式が正しくありません。';
        }
        if ($email === '') {
            $errors[] = $row_no . '行目: メールアドレスが空です。';
        } elseif (!preg_match($email_re, $email)) {
            $errors[] = $row_no . '行目: メールアドレスの形式が正しくありません。';
        } else {
            $key = strtolower($email);
            if (isset($seen[$key])) {
                $errors[] = $row_no . '行目: 同じメールアドレスが' . $seen[$key] . '行目にもあります。';
            } else {
                $seen[$key] = $row_no;
            }
        }
        if ($flag === '') {
            $errors[] = $row_no . '行目: 配信可能/不可能が空です。';
        } elseif (!isset($allow[$flag])) {
            $errors[] = $row_no . '行目: 配信可能/不可能の値が正しくありません（「配信可能」または「配信不可能」）。';
        }
        if (count($errors) >= $max_errors) {
            $errors[] = 'エラーが続くため、ここで打ち切っています。上の指摘を直してから送ってください。';
            break;
        }
    }
    if ($errors) {
        $errors[] = $stats;
    }
    return $errors;
}
