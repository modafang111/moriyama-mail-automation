from pathlib import Path

from moriyama_mail.config import load_settings
from moriyama_mail.paths import default_install_dir, repo_root


def test_default_install_dir_is_opened_repo(monkeypatch):
    monkeypatch.delenv("MORIYAMA_INSTALL_DIR", raising=False)
    root = repo_root()
    assert (root / "pyproject.toml").is_file()
    assert default_install_dir() == root


def test_load_settings_reads_env_from_install_dir(tmp_path: Path, monkeypatch):
    (tmp_path / ".env").write_text(
        "OPERATOR_NAME=cursor-local\nGOOGLE_DRIVE_MODE=mock\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("MORIYAMA_INSTALL_DIR", str(tmp_path))
    monkeypatch.setenv("MORIYAMA_DATA_DIR", str(tmp_path / "data"))
    monkeypatch.delenv("OPERATOR_NAME", raising=False)
    settings = load_settings()
    assert settings.operator_name == "cursor-local"
    assert settings.install_dir == tmp_path
