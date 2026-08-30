"""Map MyASP login and draft-mail selectors. Credentials come from .env only."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
os.environ.setdefault("MORIYAMA_INSTALL_DIR", str(ROOT))

from moriyama_mail.config import load_settings


def _dump_form(page) -> list[dict]:
    return page.evaluate(
        """() => {
          const root = document.querySelector('#MailAddMailForm') || document;
          const nodes = [...root.querySelectorAll('input, textarea, select, button, iframe')];
          return nodes.map((el) => ({
            tag: el.tagName.toLowerCase(),
            type: el.type || '',
            name: el.name || '',
            id: el.id || '',
            placeholder: el.placeholder || '',
            text: (el.innerText || el.value || '').trim().slice(0, 80),
          }));
        }"""
    )


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
        page.goto("https://my909p.com/member/item", wait_until="networkidle", timeout=60000)
        page.locator("a", has_text="テスト").first.click()
        page.wait_for_load_state("networkidle", timeout=60000)
        page.goto("https://my909p.com/member/userlist", wait_until="networkidle", timeout=60000)
        page.get_by_text("以下のアドレスに配信するメールを作成").first.click()
        page.locator("#MailAddMailForm").get_by_text("下書き保存する").wait_for(timeout=90000)
        page.screenshot(path=str(dest / "06_compose.png"), full_page=True)
        (dest / "06_compose.json").write_text(
            json.dumps({"url": page.url, "form": _dump_form(page)}, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        print("compose", page.url)
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
