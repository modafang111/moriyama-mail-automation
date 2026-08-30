"""See what happens after compose click on the テスト scenario."""

from __future__ import annotations

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

    dialogs: list[str] = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(headless=True)
        page = browser.new_page(viewport={"width": 1400, "height": 900})
        page.on("dialog", lambda d: (dialogs.append(d.message), d.accept()))
        page.goto(settings.myasp_login_url, wait_until="domcontentloaded", timeout=60000)
        page.locator("#SellerLoginid").fill(settings.myasp_user)
        page.locator("#SellerPassword").fill(settings.myasp_password)
        page.locator('button[type="submit"]:has-text("ログイン")').click()
        page.wait_for_load_state("networkidle", timeout=60000)
        page.goto(
            member_abs(settings.myasp_login_url, "/member/userlist/fM6ticMg/item_id:fM6ticMg"),
            wait_until="networkidle",
            timeout=60000,
        )
        page.get_by_role("button", name="以下のアドレスに配信するメールを作成").first.click()
        page.wait_for_timeout(5000)
        page.screenshot(path=str(dest / "07_after_compose_click.png"), full_page=True)
        (dest / "07_after_compose_click.txt").write_text(
            f"url={page.url}\ntitle={page.title()}\ndialogs={dialogs}\ntext={page.inner_text('body')[:2000]}\n",
            encoding="utf-8",
        )
        print("url", page.url)
        print("dialogs", dialogs)
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
