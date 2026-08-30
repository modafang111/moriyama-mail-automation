"""List WordPress pending requests. Does not import or send."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MORIYAMA_INSTALL_DIR", str(ROOT))

from moriyama_mail.config import load_settings
from moriyama_mail.intake.wordpress import WordPressIntakeClient


def main() -> int:
    settings = load_settings()
    client = WordPressIntakeClient(settings.wordpress_form_url, settings.wordpress_intake_token)
    pending = client.fetch_pending()
    summary = []
    for item in pending:
        summary.append(
            {
                "id": item.get("id"),
                "subject": item.get("subject"),
                "plan": item.get("myasp_plan_key"),
                "has_reader_body": bool(item.get("reader_body")),
                "body_preview": str(item.get("body") or "")[:80],
                "has_signature": bool(str(item.get("signature") or "").strip()),
            }
        )
    print(json.dumps({"count": len(summary), "requests": summary}, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
