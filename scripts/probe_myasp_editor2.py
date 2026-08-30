"""Inspect MyASP editor2 iframe and JS API. Does not save."""

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
        page.locator("iframe.editor2-body-frame").wait_for(timeout=90000)
        page.wait_for_timeout(2500)
        api = page.evaluate(
            """() => {
              const keys = Object.keys(window).filter((k) => /editor|Editor|tinymce|CKEDITOR/i.test(k));
              const info = { keys, hasJQuery: typeof window.jQuery === 'function' };
              if (window.jQuery) {
                const $ = window.jQuery;
                info.editor2fn = typeof $.fn.editor2;
                info.dataKeys = Object.keys($('.editor2-body_origin').data() || {});
              }
              return info;
            }"""
        )
        frame = page.frame_locator("iframe.editor2-body-frame")
        inner = None
        try:
            inner = page.evaluate(
                """() => {
                  const iframe = document.querySelector('iframe.editor2-body-frame');
                  const doc = iframe && iframe.contentDocument;
                  if (!doc) return { error: 'no doc' };
                  return {
                    ready: doc.readyState,
                    html: (doc.body && doc.body.innerHTML || '').slice(0, 2500),
                    text: (doc.body && doc.body.innerText || '').slice(0, 500),
                    nodes: [...doc.querySelectorAll('textarea, input, [contenteditable], pre, div')].slice(0, 30).map((el) => ({
                      tag: el.tagName.toLowerCase(),
                      id: el.id || '',
                      cls: (el.className || '').toString().slice(0, 80),
                      contenteditable: el.getAttribute('contenteditable') || '',
                      value: (el.value || el.innerText || '').slice(0, 150),
                    })),
                  };
                }"""
            )
        except Exception as exc:
            inner = {"error": str(exc)}
        payload = {"api": api, "inner": inner}
        (dest / "10_editor2.json").write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        print(json.dumps(api, ensure_ascii=False, indent=2))
        print("INNER_TEXT=", (inner or {}).get("text", "")[:300])
        print("INNER_NODES=", json.dumps((inner or {}).get("nodes"), ensure_ascii=False, indent=2)[:2000])
        browser.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
