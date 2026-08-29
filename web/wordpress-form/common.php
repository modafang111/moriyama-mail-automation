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
    foreach (['pending', 'done', 'files'] as $name) {
        $path = $dir . '/' . $name;
        if (!is_dir($path)) {
            mkdir($path, 0750, true);
        }
    }
    return $dir;
}

function intake_json_header(): void
{
    header('Content-Type: application/json; charset=utf-8');
}

function intake_token_ok(string $token): bool
{
    return hash_equals(INTAKE_TOKEN, $token);
}
