"""Open a campaign's MyASP draft and confirm 件名 + 修正後. Does not send."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MORIYAMA_INSTALL_DIR", str(ROOT))

from moriyama_mail.bootstrap import build_service
from moriyama_mail.myasp.browser import LOGIN_ID, LOGIN_PASSWORD, LOGIN_SUBMIT, member_abs


def main() -> int:
    campaign_id = sys.argv[1] if len(sys.argv) > 1 else "C-20260830-EC3A"
    service = build_service()
    campaign = service.get(campaign_id)
    dest = ROOT / "data" / "myasp-draft"
    dest.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    settings = service.settings
    scenario_id = "fM6ticMg"
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(settings.myasp_login_url, wait_until="domcontentloaded", timeout=60000)
        page.locator(LOGIN_ID).fill(settings.myasp_user)
        page.locator(LOGIN_PASSWORD).fill(settings.myasp_password)
        page.locator(LOGIN_SUBMIT).click()
        page.wait_for_load_state("networkidle", timeout=60000)
        page.goto(
            member_abs(settings.myasp_login_url, f"/member/mailhistory/{scenario_id}/item_id:{scenario_id}"),
            wait_until="networkidle",
            timeout=60000,
        )
        row = page.locator("tr", has_text=campaign.subject).first
        row.get_by_text("編集").first.click()
        page.locator("#MailSubject").wait_for(timeout=90000)
        page.wait_for_timeout(1500)
        page.screenshot(path=str(dest / "09_revised_edit.png"), full_page=True)
        values = page.evaluate(
            """() => ({
              subject: document.querySelector('#MailSubject')?.value || '',
              body: document.querySelector('input[name="data[Mail][body]"]')?.value || '',
            })"""
        )
        browser.close()
    saved_subject = values.get("subject") or ""
    saved_body = values.get("body") or ""
    report = {
        "campaign_id": campaign.id,
        "subject_ok": campaign.subject == saved_subject,
        "has_placeholder": "{{DRIVE_SHARE_URL}}" in saved_body,
        "has_original": "バイリンク" in saved_body and "ご確認" in saved_body or "お世話" in saved_body,
        "has_signature": "盛山英幸" in saved_body,
        "saved_subject": saved_subject,
    }
    (dest / "09_revised_edit.json").write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0 if report["subject_ok"] and report["has_placeholder"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
