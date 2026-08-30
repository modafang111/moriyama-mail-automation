"""Send pending WordPress requests via cloud-agent-sync notify_job."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MORIYAMA_INSTALL_DIR", str(ROOT))

from moriyama_mail.config import load_settings
from moriyama_mail.intake.wordpress import WordPressIntakeClient
from moriyama_mail.notify.mailer import notify_wordpress_payload


def main() -> int:
    load_settings()
    client = WordPressIntakeClient(
        os.getenv("WORDPRESS_FORM_URL", "").strip(),
        os.getenv("WORDPRESS_INTAKE_TOKEN", "").strip(),
    )
    pending = client.fetch_pending()
    if not pending:
        print("新しい依頼はありません。")
        return 0
    failed = 0
    for payload in pending:
        ok = notify_wordpress_payload(payload)
        print("sent" if ok else "failed", payload.get("id"))
        if not ok:
            failed += 1
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
