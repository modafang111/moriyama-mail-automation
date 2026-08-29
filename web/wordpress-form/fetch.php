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

$action = (string)($_POST['action'] ?? 'list');
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

$requests = [];
foreach (glob(intake_data_dir() . '/pending/*.json') ?: [] as $file) {
    $record = json_decode((string)file_get_contents($file), true);
    if (!is_array($record)) {
        continue;
    }
    foreach (['material', 'additions_csv', 'exclusions_csv'] as $key) {
        $info = $record[$key] ?? null;
        if (!is_array($info) || empty($info['path']) || !is_file($info['path'])) {
            $record[$key] = null;
            continue;
        }
        $record[$key] = [
            'filename' => (string)($info['filename'] ?? basename($info['path'])),
            'content_base64' => base64_encode((string)file_get_contents($info['path'])),
        ];
    }
    $requests[] = $record;
}

echo json_encode(['ok' => true, 'requests' => $requests], JSON_UNESCAPED_UNICODE);
