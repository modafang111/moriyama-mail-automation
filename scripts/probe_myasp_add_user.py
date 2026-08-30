"""Map the individual user-registration form for scenario テスト."""

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
            member_abs(settings.myasp_login_url, "/member/add_user/fM6ticMg/item_id:fM6ticMg"),
            wait_until="networkidle",
            timeout=60000,
        )
        page.screenshot(path=str(dest / "08_add_user.png"), full_page=True)
        fields = page.evaluate(
            """() => [...document.querySelectorAll('input, textarea, select, button')].map((el) => ({
              tag: el.tagName.toLowerCase(),
              type: el.type || '',
              name: el.name || '',
              id: el.id || '',
              placeholder: el.placeholder || '',
              text: (el.innerText || el.value || '').trim().slice(0, 80),
            }))"""
        )
        (dest / "08_add_user.json").write_text(
            json.dumps({"url": page.url, "title": page.title(), "fields": fields}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print(page.url, page.title())
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
