import pytest

from moriyama_mail.intake.wordpress_deploy import (
    STATIC_FILES,
    FORM_DIR,
    collect_uploads,
    remote_store_target,
    render_config_php,
)


def test_render_config_php_uses_token():
    text = render_config_php("secret-token").decode("utf-8")
    assert "secret-token" in text
    assert "replace-this-intake-token" not in text
    assert "NOTIFY_" not in text


def test_render_config_php_includes_notify_settings():
    text = render_config_php(
        "secret-token",
        {
            "to": "modafang111@gmail.com",
            "from": "modafang111@gmail.com",
            "password": "secret-pass",
            "host": "smtp.gmail.com",
            "port": "587",
        },
    ).decode("utf-8")
    assert "NOTIFY_TO" in text
    assert "smtp.gmail.com" in text
    assert "secret-pass" in text


def test_render_config_php_escapes_quotes():
    text = render_config_php("a'b\\c").decode("utf-8")
    assert "a\\'b\\\\c" in text


def test_remote_store_target_uses_cwd_and_basename():
    directory, name = remote_store_target("public_html/mail-request", "data/.htaccess")
    assert directory == "public_html/mail-request/data"
    assert name == ".htaccess"
    directory, name = remote_store_target("public_html/mail-request", "index.php")
    assert directory == "public_html/mail-request"
    assert name == "index.php"


def test_collect_uploads_includes_form_files_and_generated_config():
    uploads = collect_uploads("local-test-token")
    names = [name for name, _payload in uploads]
    for relative in STATIC_FILES:
        assert relative in names
        assert (FORM_DIR / relative).is_file()
    assert names.count("config.php") == 1
    config = dict(uploads)["config.php"].decode("utf-8")
    assert "local-test-token" in config


def test_deploy_script_dry_run_lists_files(monkeypatch):
    import os
    import subprocess
    import sys
    from pathlib import Path

    monkeypatch.setenv("WORDPRESS_INTAKE_TOKEN", "local-test-token")
    monkeypatch.setenv("WORDPRESS_FTP_HOST", "")
    root = Path(__file__).resolve().parents[1]
    env = os.environ.copy()
    env["PYTHONPATH"] = str(root / "src")
    result = subprocess.run(
        [sys.executable, str(root / "scripts" / "deploy_wordpress_form.py"), "--dry-run"],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
    assert "index.php" in result.stdout
    assert "config.php" in result.stdout
    assert "Dry run" in result.stdout


def test_collect_uploads_rejects_placeholder_token():
    with pytest.raises(ValueError):
        collect_uploads("replace-this-intake-token")
    with pytest.raises(ValueError):
        collect_uploads("")
