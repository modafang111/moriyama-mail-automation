"""Save 件名 + 修正後 to MyASP as a draft. Does not send."""

from __future__ import annotations

import os
import sys
from datetime import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MORIYAMA_INSTALL_DIR", str(ROOT))

from moriyama_mail.bootstrap import build_service
from moriyama_mail.domain.placeholders import draft_reader_body
from moriyama_mail.intake.request import CampaignRequest
from moriyama_mail.notify.mailer import format_request_notice


def main() -> int:
    service = build_service()
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    original = "フォームからの依頼です。資料をご確認ください。"
    signature = service.settings.mail_signature
    subject = f"【自動化確認】修正後下書き {stamp}"
    revised = draft_reader_body(original, "", service.settings.drive_link_label, signature)
    _, notice = format_request_notice(
        request_id="local-check",
        subject=subject,
        plan="テスト",
        message_body=original,
        signature=signature,
    )
    if revised not in notice:
        print("revised-body-not-in-notice")
        return 2
    campaign = service.submit_request(
        CampaignRequest(
            subject=subject,
            body=original,
            signature=signature,
            myasp_plan_key="test_plan",
            source_channel="wordpress_form",
        )
    )
    print(f"campaign={campaign.id}")
    print(f"error={campaign.error_message or ''}")
    print("revised-match" if campaign.body == revised else "revised-mismatch")
    print("placeholder" if "{{DRIVE_SHARE_URL}}" in campaign.body else "missing-placeholder")
    if campaign.error_message or campaign.body != revised:
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
