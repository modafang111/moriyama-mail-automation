from __future__ import annotations

import os
import sys
from pathlib import Path


APP_DIR_NAME = "MoriyamaMailAutomation"


def default_install_dir() -> Path:
    if os.name == "nt":
        return Path(r"D:\dev\moriyama-mail-automation")
    return Path.cwd()


def data_dir() -> Path:
    override = os.getenv("MORIYAMA_DATA_DIR", "").strip()
    if override:
        path = Path(override)
    elif os.name == "nt":
        local = os.getenv("LOCALAPPDATA") or str(Path.home() / "AppData" / "Local")
        path = Path(local) / APP_DIR_NAME
    else:
        path = Path(os.getenv("XDG_DATA_HOME", Path.home() / ".local" / "share")) / APP_DIR_NAME
    path.mkdir(parents=True, exist_ok=True)
    (path / "imports").mkdir(exist_ok=True)
    (path / "drive_mock").mkdir(exist_ok=True)
    return path


def secrets_dir() -> Path:
    path = data_dir() / "secrets"
    path.mkdir(parents=True, exist_ok=True)
    return path


def database_path() -> Path:
    return data_dir() / "moriyama.sqlite3"


def is_frozen() -> bool:
    return getattr(sys, "frozen", False)
