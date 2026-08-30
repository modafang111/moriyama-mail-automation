"""Retry MyASP draft save for campaigns that failed. Does not send."""

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
    failed = [item for item in service.list_campaigns() if item.error_message]
    print(f"retry={len(failed)}")
    bad = 0
    for campaign in failed:
        try:
            saved = service.save_myasp_draft(campaign)
            print("ok", saved.id, saved.subject)
        except Exception as exc:
            bad += 1
            print("fail", campaign.id, str(exc)[:160])
    return 2 if bad else 0


if __name__ == "__main__":
    raise SystemExit(main())
