"""Dump compose-page body editors. Does not save or send."""

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


def dump_editors(page) -> dict:
    main = page.evaluate(
        """() => {
          const nodes = [...document.querySelectorAll('textarea, input[name*="body"], [contenteditable], iframe')];
          return {
            url: location.href,
            hidden: document.querySelector('input[name="data[Mail][body]"]')?.value || '',
            mailType: document.querySelector('#MailMailType')?.checked || false,
            nodes: nodes.map((el) => ({
              tag: el.tagName.toLowerCase(),
              type: el.type || '',
              name: el.name || '',
              id: el.id || '',
              cls: el.className?.toString?.().slice(0, 80) || '',
              visible: !!(el.offsetWidth || el.offsetHeight),
              value: (el.value || el.innerText || '').slice(0, 120),
            })),
          };
        }"""
    )
    frames = []
    for frame in page.frames:
        if frame == page.main_frame:
            continue
        try:
            frames.append(
                {
                    "url": frame.url,
                    "name": frame.name,
                    "text": (frame.locator("body").inner_text() if frame.locator("body").count() else "")[:200],
                }
            )
        except Exception as exc:
            frames.append({"url": frame.url, "error": str(exc)})
    main["frames"] = frames
    return main


def main() -> int:
    settings = load_settings()
    dest = ROOT / "data" / "myasp-probe"
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
            member_abs(settings.myasp_login_url, f"/member/userlist/{SCENARIO_ID}/item_id:{SCENARIO_ID}"),
            wait_until="networkidle",
            timeout=60000,
        )
        page.get_by_role("button", name="以下のアドレスに配信するメールを作成").first.click()
        page.locator("#MailAddMailForm").locator('button[name="Submit[draft_save]"]').wait_for(timeout=90000)
        page.wait_for_timeout(3000)
        before = dump_editors(page)
        (dest / "09_body_before.json").write_text(json.dumps(before, ensure_ascii=False, indent=2), encoding="utf-8")
        page.screenshot(path=str(dest / "09_body_before.png"), full_page=True)
        print("BEFORE hidden", (before.get("hidden") or "")[:80])
        print("nodes", json.dumps(before.get("nodes"), ensure_ascii=False, indent=2))
        print("frames", json.dumps(before.get("frames"), ensure_ascii=False, indent=2))
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
