"""Save one labeled MyASP draft. Does not send or reserve."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MORIYAMA_INSTALL_DIR", str(ROOT))

from moriyama_mail.bootstrap import build_service


def main() -> int:
    service = build_service()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    campaign = service.create_campaign(
        subject=f"【自動化確認】下書き保存 {stamp}",
        body="これは配信していません。共有URLは仮置きの動作確認です。",
        notes="自動化の下書き確認。配信しない。",
        myasp_plan_key="test_plan",
    )
    service.save_myasp_draft(campaign)
    dest = ROOT / "data" / "myasp-draft"
    print(f"saved draft for {campaign.id}")
    print(f"screenshots: {dest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
