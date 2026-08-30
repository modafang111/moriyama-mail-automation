"""Download intake timing logs from the live form and print them."""

from __future__ import annotations

import os
import sys
from ftplib import FTP, FTP_TLS, error_perm
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MORIYAMA_INSTALL_DIR", str(ROOT))

from moriyama_mail.config import load_settings
from moriyama_mail.intake.wordpress import WordPressIntakeClient


def _out_dir() -> Path:
    dest = ROOT / "data" / "wordpress-logs"
    dest.mkdir(parents=True, exist_ok=True)
    return dest


def _print_log(name: str, text: str) -> None:
    print()
    print("====", name, "====")
    print(text.rstrip() or "(empty)")


def fetch_via_http() -> list[tuple[str, str]]:
    load_settings()
    client = WordPressIntakeClient(
        os.getenv("WORDPRESS_FORM_URL", "").strip(),
        os.getenv("WORDPRESS_INTAKE_TOKEN", "").strip(),
    )
    items = client.fetch_logs()
    dest = _out_dir()
    found: list[tuple[str, str]] = []
    for item in items:
        name = str(item.get("name") or "log.txt")
        text = str(item.get("text") or "")
        (dest / name).write_text(text, encoding="utf-8")
        found.append((name, text))
        _print_log(name, text)
    return found


def _connect() -> FTP:
    host = os.getenv("WORDPRESS_FTP_HOST", "").strip()
    user = os.getenv("WORDPRESS_FTP_USER", "").strip()
    password = os.getenv("WORDPRESS_FTP_PASSWORD", "")
    port = int(os.getenv("WORDPRESS_FTP_PORT") or "21")
    use_tls = (os.getenv("WORDPRESS_FTP_TLS") or "1").strip().lower() not in {"0", "false", "no"}
    if not host or not user or not password:
        raise SystemExit("Set WORDPRESS_FTP_HOST, WORDPRESS_FTP_USER, WORDPRESS_FTP_PASSWORD.")
    if use_tls:
        client: FTP = FTP_TLS()
        client.connect(host, port, timeout=30)
        client.login(user, password)
        client.prot_p()
    else:
        client = FTP()
        client.connect(host, port, timeout=30)
        client.login(user, password)
    client.set_pasv(True)
    return client


def _download(ftp: FTP, remote: str) -> bytes | None:
    buf = BytesIO()
    try:
        ftp.retrbinary(f"RETR {remote}", buf.write)
    except error_perm:
        return None
    return buf.getvalue()


def fetch_via_ftp() -> list[tuple[str, str]]:
    load_settings()
    remote_dir = (os.getenv("WORDPRESS_FTP_REMOTE_DIR") or "public_html/mail-request").strip().replace("\\", "/")
    dest = _out_dir()
    found: list[tuple[str, str]] = []
    ftp = _connect()
    try:
        home = ftp.pwd()
        for part in [p for p in remote_dir.split("/") if p]:
            ftp.cwd(part)
        candidates = ["error_log", "data/logs"]
        names: list[str] = []
        try:
            ftp.cwd("data/logs")
            names = [name for name in ftp.nlst() if name.endswith(".log") or name.endswith(".txt")]
            ftp.cwd(home)
            for part in [p for p in remote_dir.split("/") if p]:
                ftp.cwd(part)
            candidates = [f"data/logs/{name}" for name in names] + ["error_log"]
        except error_perm:
            ftp.cwd(home)
            for part in [p for p in remote_dir.split("/") if p]:
                try:
                    ftp.cwd(part)
                except error_perm:
                    pass
        for remote in candidates:
            raw = _download(ftp, remote)
            if raw is None:
                continue
            name = remote.replace("/", "_")
            text = raw.decode("utf-8", errors="replace")
            (dest / name).write_text(text, encoding="utf-8")
            found.append((name, text))
            _print_log(name, text)
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()
    return found


def main() -> int:
    print("Fetching intake logs from the live form.")
    http_items = []
    try:
        http_items = fetch_via_http()
    except Exception as exc:
        print("HTTP:", exc)
    ftp_items = []
    try:
        ftp_items = fetch_via_ftp()
    except Exception as exc:
        print("FTP:", type(exc).__name__)
    if not http_items and not ftp_items:
        print("No log files yet. Submit the form once, then run this again.")
        return 0
    print()
    print("Saved under", _out_dir())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
