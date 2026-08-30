"""Open the latest automation draft and dump saved values. Does not send."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MORIYAMA_INSTALL_DIR", str(ROOT))

from moriyama_mail.config import load_settings
from moriyama_mail.myasp.browser import member_abs

SCENARIO_ID = "fM6ticMg"
SUBJECT_PREFIX = sys.argv[1] if len(sys.argv) > 1 else "【自動化確認】"


def main() -> int:
    settings = load_settings()
    dest = ROOT / "data" / "myasp-draft"
    dest.mkdir(parents=True, exist_ok=True)
    from playwright.sync_api import sync_playwright

    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.goto(settings.myasp_login_url, wait_until="domcontentloaded", timeout=60000)
        page.locator("#SellerLoginid").fill(settings.myasp_user)
        page.locator("#SellerPassword").fill(settings.myasp_password)
        page.locator('button[type="submit"]:has-text("ログイン")').click()
        page.wait_for_load_state("networkidle", timeout=60000)
        page.goto(
            member_abs(settings.myasp_login_url, f"/member/mailhistory/{SCENARIO_ID}/item_id:{SCENARIO_ID}"),
            wait_until="networkidle",
            timeout=60000,
        )
        page.screenshot(path=str(dest / "07_verify_list.png"), full_page=True)
        listing = page.evaluate(
            """(prefix) => {
              const rows = [...document.querySelectorAll('tr')].map((tr) => tr.innerText.replace(/\\s+/g, ' ').trim());
              return rows.filter((t) => t.includes(prefix)).slice(0, 5);
            }""",
            SUBJECT_PREFIX,
        )
        edit = page.locator("tr", has_text=SUBJECT_PREFIX).first.get_by_role("link", name="編集")
        if edit.count() == 0:
            edit = page.locator("tr", has_text=SUBJECT_PREFIX).first.locator("a", has_text="編集")
        edit.first.click()
        page.locator("#MailSubject").wait_for(timeout=90000)
        page.wait_for_timeout(2000)
        page.screenshot(path=str(dest / "08_verify_edit.png"), full_page=True)
        values = page.evaluate(
            """() => ({
              url: location.href,
              title: document.title,
              subject: document.querySelector('#MailSubject')?.value || '',
              body: document.querySelector('input[name="data[Mail][body]"]')?.value || '',
              memo: document.querySelector('#MailMemo')?.value || '',
              banner: document.body.innerText.includes('下書きとして保存しました'),
              hasDraftSave: !!document.querySelector('#MailAddMailForm button[name="Submit[draft_save]"]'),
              hasConfirm: !!document.querySelector('button[name="Submit[mail_save]"]'),
            })"""
        )
        values["listing"] = listing
        values["has_body_text"] = bool((values.get("body") or "").strip()) and "買取案件紹介" in (
            values.get("body") or ""
        )
        values["has_drive_placeholder"] = "{{DRIVE_SHARE_URL}}" in (values.get("body") or "")
        values["has_unsubscribe"] = "%unsubscribe%" in (values.get("body") or "") or "%cancelurl%" in (
            values.get("body") or ""
        )
        values["has_privacy"] = "プライバシーポリシー" in (values.get("body") or "")
        values["subject_ok"] = SUBJECT_PREFIX in (values.get("subject") or "")
        values["memo_ok"] = "受付番号" in (values.get("memo") or "")
        values["list_is_draft"] = any("下書き" in row and SUBJECT_PREFIX in row for row in listing)
        values["list_not_sent"] = all("配信済み" not in row or SUBJECT_PREFIX not in row for row in listing) or any(
            "下書き" in row and SUBJECT_PREFIX in row for row in listing
        )
        (dest / "08_verify_edit.json").write_text(json.dumps(values, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps({k: values[k] for k in values if k != "body"}, ensure_ascii=False, indent=2))
        print("BODY_PREVIEW=")
        print((values.get("body") or "")[:800])
        browser.close()
        ok = (
            values["subject_ok"]
            and values["has_body_text"]
            and values["list_is_draft"]
            and values["has_unsubscribe"]
            and values.get("has_drive_placeholder", True)
        )
        return 0 if ok else 2


if __name__ == "__main__":
    raise SystemExit(main())
