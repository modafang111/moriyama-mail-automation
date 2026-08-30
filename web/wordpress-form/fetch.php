<?php
require __DIR__ . '/common.php';
intake_load_config(true);
intake_json_header();

$token = (string)($_GET['token'] ?? $_POST['token'] ?? '');
if (!intake_token_ok($token)) {
    http_response_code(403);
    echo json_encode(['ok' => false, 'error' => 'token'], JSON_UNESCAPED_UNICODE);
    exit;
}

$action = (string)($_POST['action'] ?? $_GET['action'] ?? 'list');
if ($action === 'logs') {
    $files = array_merge(
        glob(intake_data_dir() . '/logs/*.log') ?: [],
        glob(intake_data_dir() . '/logs/*.txt') ?: []
    );
    usort($files, function ($a, $b) {
        return filemtime($b) <=> filemtime($a);
    });
    $out = [];
    foreach (array_slice($files, 0, 20) as $file) {
        $text = (string)file_get_contents($file);
        if (strlen($text) > 200000) {
            $text = substr($text, -200000);
        }
        $out[] = [
            'name' => basename($file),
            'mtime' => gmdate('c', filemtime($file)),
            'bytes' => strlen($text),
            'text' => $text,
        ];
    }
    echo json_encode(['ok' => true, 'logs' => $out], JSON_UNESCAPED_UNICODE);
    exit;
}
if ($action === 'imported') {
    $ids = array_filter(array_map('trim', explode(',', (string)($_POST['ids'] ?? ''))));
    foreach ($ids as $id) {
        if (!preg_match('/^[A-Za-z0-9-]+$/', $id)) {
            continue;
        }
        $from = intake_data_dir() . '/pending/' . $id . '.json';
        $to = intake_data_dir() . '/done/' . $id . '.json';
        if (is_file($from)) {
            rename($from, $to);
        }
    }
    echo json_encode(['ok' => true], JSON_UNESCAPED_UNICODE);
    exit;
}

function intake_attach_files(array $record, bool $include_bytes): array
{
    foreach (['material', 'additions_csv', 'exclusions_csv'] as $key) {
        $info = $record[$key] ?? null;
        if (!is_array($info) || empty($info['path']) || !is_file($info['path'])) {
            $record[$key] = null;
            continue;
        }
        $payload = [
            'filename' => (string)($info['filename'] ?? basename($info['path'])),
            'bytes' => filesize($info['path']),
        ];
        if ($include_bytes) {
            $payload['content_base64'] = base64_encode((string)file_get_contents($info['path']));
        }
        $record[$key] = $payload;
    }
    return $record;
}

$item_id = trim((string)($_GET['id'] ?? $_POST['id'] ?? ''));
if ($action === 'item' && $item_id !== '' && preg_match('/^[A-Za-z0-9-]+$/', $item_id)) {
    $path = intake_data_dir() . '/pending/' . $item_id . '.json';
    if (!is_file($path)) {
        echo json_encode(['ok' => false, 'error' => 'not_found'], JSON_UNESCAPED_UNICODE);
        exit;
    }
    $record = json_decode((string)file_get_contents($path), true);
    if (!is_array($record)) {
        echo json_encode(['ok' => false, 'error' => 'broken'], JSON_UNESCAPED_UNICODE);
        exit;
    }
    echo json_encode(['ok' => true, 'request' => intake_attach_files($record, true)], JSON_UNESCAPED_UNICODE);
    exit;
}

$requests = [];
foreach (glob(intake_data_dir() . '/pending/*.json') ?: [] as $file) {
    $record = json_decode((string)file_get_contents($file), true);
    if (!is_array($record)) {
        continue;
    }
    $requests[] = intake_attach_files($record, false);
}

echo json_encode(['ok' => true, 'requests' => $requests], JSON_UNESCAPED_UNICODE);
