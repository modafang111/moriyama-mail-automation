"""Create a local venv so Cursor can run this project."""

from __future__ import annotations

import os
import subprocess
import sys
import venv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
VENV = ROOT / ".venv"


def venv_python() -> Path:
    if os.name == "nt":
        return VENV / "Scripts" / "python.exe"
    return VENV / "bin" / "python"


def main() -> int:
    if sys.version_info < (3, 11):
        print("Python 3.11 or newer is required.")
        print("This interpreter:", sys.version)
        return 1

    python = venv_python()
    if not python.is_file():
        print("Creating", VENV)
        venv.create(VENV, with_pip=True)

    subprocess.check_call([str(python), "-m", "pip", "install", "--upgrade", "pip"])
    subprocess.check_call([str(python), "-m", "pip", "install", "-r", str(ROOT / "requirements-dev.txt")])
    subprocess.check_call([str(python), "-m", "pip", "install", "-e", str(ROOT)])

    env_path = ROOT / ".env"
    example = ROOT / ".env.example"
    if not env_path.is_file() and example.is_file():
        env_path.write_bytes(example.read_bytes())
        print("Created .env")

    print()
    print("Setup finished.")
    print("In Cursor: Python: Select Interpreter ->", python)
    print("Then Run and Debug -> 担当者画面")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
