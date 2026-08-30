"""Upload the dedicated form to WordPress-123.com via FTP."""

from __future__ import annotations

import argparse
import os
from ftplib import FTP, FTP_TLS, error_perm
from io import BytesIO

from moriyama_mail.config import load_settings
from moriyama_mail.intake.wordpress_deploy import collect_uploads, remote_store_target


def load_deploy_env() -> None:
    load_settings()


def _connect(host: str, port: int, user: str, password: str, use_tls: bool) -> FTP:
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


def _ensure_dirs(ftp: FTP, remote_dir: str, home: str) -> None:
    parts = [part for part in remote_dir.replace("\\", "/").strip("/").split("/") if part]
    ftp.cwd(home)
    for part in parts:
        try:
            ftp.mkd(part)
        except error_perm:
            pass
        ftp.cwd(part)


def deploy(uploads: list[tuple[str, bytes]], *, dry_run: bool = False) -> list[str]:
    load_deploy_env()
    host = os.getenv("WORDPRESS_FTP_HOST", "").strip()
    user = os.getenv("WORDPRESS_FTP_USER", "").strip()
    password = os.getenv("WORDPRESS_FTP_PASSWORD", "")
    remote_dir = (os.getenv("WORDPRESS_FTP_REMOTE_DIR") or "public_html/mail-request").strip()
    port = int(os.getenv("WORDPRESS_FTP_PORT") or "21")
    use_tls = (os.getenv("WORDPRESS_FTP_TLS") or "1").strip().lower() not in {"0", "false", "no"}

    names = [name for name, _payload in uploads]
    if dry_run:
        print("Dry run. Files:")
        for name in names:
            print(" ", name)
        print("Remote dir:", remote_dir)
        print("Host:", host or "(not set)")
        return names

    if not host or not user:
        raise SystemExit("Set WORDPRESS_FTP_HOST and WORDPRESS_FTP_USER in .env.")
    if not password:
        raise SystemExit("Set WORDPRESS_FTP_PASSWORD in .env.")

    print("Uploading to", host, remote_dir)
    ftp = _connect(host, port, user, password, use_tls)
    try:
        home = ftp.pwd()
        for relative, payload in uploads:
            directory, name = remote_store_target(remote_dir, relative)
            if directory:
                _ensure_dirs(ftp, directory, home)
            else:
                ftp.cwd(home)
            ftp.storbinary(f"STOR {name}", BytesIO(payload))
            print("OK", relative)
    finally:
        try:
            ftp.quit()
        except Exception:
            ftp.close()
    print("Done. Form URL: https://wordpress-123.com/mail-request/")
    return names


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    load_deploy_env()
    token = os.getenv("WORDPRESS_INTAKE_TOKEN", "").strip()
    try:
        uploads = collect_uploads(token)
    except (ValueError, FileNotFoundError) as exc:
        raise SystemExit(str(exc)) from exc
    deploy(uploads, dry_run=args.dry_run)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
