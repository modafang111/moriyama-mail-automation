"""Import WordPress pending requests and save 件名 + 修正後 as MyASP drafts. Does not send."""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MORIYAMA_INSTALL_DIR", str(ROOT))

from moriyama_mail.bootstrap import build_service


def main() -> int:
    service = build_service()
    campaigns = service.import_wordpress_requests()
    print(f"imported={len(campaigns)}")
    failed = 0
    for campaign in campaigns:
        mark = "ok" if not campaign.error_message else "fail"
        if campaign.error_message:
            failed += 1
        print(f"{mark} {campaign.id} {campaign.subject}")
        print("placeholder" if "{{DRIVE_SHARE_URL}}" in campaign.body else "missing-placeholder")
    return 2 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
