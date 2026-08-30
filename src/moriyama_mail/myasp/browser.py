"""Save a MyASP bulk-mail draft via the management screen. Does not send."""

from __future__ import annotations

from pathlib import Path
from urllib.parse import urlparse

from moriyama_mail.config import Settings
from moriyama_mail.paths import repo_root
from moriyama_mail.domain.models import (
    AudienceChangeSet,
    Campaign,
    DeliveryMode,
    DeliveryResult,
    utc_now,
)
from moriyama_mail.myasp.gateway import MyAspMailDraft

LOGIN_ID = "#SellerLoginid"
LOGIN_PASSWORD = "#SellerPassword"
LOGIN_SUBMIT = 'button[type="submit"]:has-text("ログイン")'
COMPOSE_CREATE = "以下のアドレスに配信するメールを作成"
SUBJECT = "#MailSubject"
BODY_HIDDEN = 'input[name="data[Mail][body]"]'
DRAFT_SAVE = 'button[name="Submit[draft_save]"]'
CONFIRM = 'button[name="Submit[mail_save]"]'
MEMO = "#MailMemo"
FORM = "#MailAddMailForm"


def member_abs(login_url: str, path: str) -> str:
    parsed = urlparse(login_url)
    if not path.startswith("/"):
        path = "/" + path
    return f"{parsed.scheme}://{parsed.netloc}{path}"


def _plain_text(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n").strip()


def merge_body_with_footer(existing: str, text: str) -> str:
    payload = (text or "").rstrip()
    footer = (existing or "").strip()
    if not footer:
        return payload
    keep_markers = ("%unsubscribe%", "%cancelurl%", "プライバシーポリシー")
    if any(marker in footer for marker in keep_markers) and not any(marker in payload for marker in keep_markers):
        return f"{payload}\n\n{footer}\n"
    return payload


class BrowserMyAspGateway:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def apply_audience(self, campaign: Campaign, changes: AudienceChangeSet) -> str:
        return f"MyASP読者反映は未実装です（add={changes.add_count}）。"

    def create_mail(self, campaign: Campaign) -> MyAspMailDraft:
        if not self.settings.myasp_login_url or not self.settings.myasp_user or not self.settings.myasp_password:
            raise RuntimeError("MYASP_LOGIN_URL / MYASP_USER / MYASP_PASSWORD を .env に入れてください。")
        plan = self.settings.plan_by_key(campaign.myasp_plan_key)
        scenario_id = (plan.scenario_id if plan else "").strip()
        scenario_name = (campaign.myasp_plan_name or (plan.name if plan else "") or "テスト").strip()
        self._save_draft(campaign.subject, campaign.body, scenario_name, scenario_id, memo=campaign.id)
        return MyAspMailDraft(
            subject=campaign.subject,
            body=campaign.body,
            scenario_id=scenario_id,
            mock=False,
        )

    def send(self, campaign: Campaign, mode: DeliveryMode, recipients: tuple[str, ...]) -> DeliveryResult:
        return DeliveryResult(
            ok=False,
            mode=mode,
            executed_at=utc_now(),
            target_count=0,
            exclude_count=campaign.audience.exclude_count,
            error="MyASP実配信は未実装です。下書き保存のみ対応しています。",
            mock=False,
        )

    def _save_draft(
        self,
        subject: str,
        body: str,
        scenario_name: str,
        scenario_id: str = "",
        memo: str = "",
    ) -> None:
        from playwright.sync_api import sync_playwright

        dest = repo_root() / "data" / "myasp-draft"
        dest.mkdir(parents=True, exist_ok=True)
        (self.settings.data_dir / "myasp-draft").mkdir(parents=True, exist_ok=True)
        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=True)
            page = browser.new_page(viewport={"width": 1400, "height": 900})
            page.on("dialog", lambda dialog: dialog.accept())
            try:
                self._login(page)
                self._shot(page, dest, "01_after_login.png")
                self._open_userlist(page, scenario_name, scenario_id)
                self._shot(page, dest, "02_userlist.png")
                self._ensure_recipient(page, scenario_id, dest)
                self._shot(page, dest, "03_userlist_ready.png")
                page.get_by_role("button", name=COMPOSE_CREATE).first.click()
                try:
                    page.locator(FORM).locator(DRAFT_SAVE).wait_for(timeout=90000)
                except Exception:
                    self._shot(page, dest, "03b_compose_failed.png")
                    raise RuntimeError("メール作成画面が開きませんでした。配信はしていません。")
                page.locator(SUBJECT).wait_for(timeout=30000)
                page.locator("iframe.editor2-body-frame").wait_for(timeout=30000)
                page.locator(SUBJECT).fill(subject)
                saved_body = self._fill_body(page, body)
                if _plain_text(body) not in _plain_text(saved_body):
                    raise RuntimeError("本文が作成画面に入りませんでした。配信はしていません。")
                if memo:
                    page.locator(MEMO).fill(f"受付番号 {memo}")
                self._shot(page, dest, "04_before_save.png")
                page.locator(FORM).locator(DRAFT_SAVE).click()
                page.wait_for_load_state("networkidle", timeout=60000)
                self._shot(page, dest, "05_after_save.png")
                self._assert_not_confirm(page)
                if scenario_id:
                    page.goto(
                        member_abs(self.settings.myasp_login_url, f"/member/mailhistory/{scenario_id}/item_id:{scenario_id}"),
                        wait_until="networkidle",
                        timeout=60000,
                    )
                    self._shot(page, dest, "06_mailhistory.png")
                    if subject not in (page.inner_text("body") or ""):
                        raise RuntimeError("下書き保存後のメール一覧に件名が見つかりません。配信はしていません。")
            finally:
                browser.close()

    def _shot(self, page, dest: Path, name: str) -> None:
        page.screenshot(path=str(dest / name), full_page=True)
        alt = self.settings.data_dir / "myasp-draft" / name
        if alt.parent != dest:
            alt.parent.mkdir(parents=True, exist_ok=True)
            try:
                alt.write_bytes((dest / name).read_bytes())
            except OSError:
                pass

    def _userlist_empty(self, page) -> bool:
        text = page.inner_text("body") or ""
        return "選択できるユーザーがいません" in text or "宛先数０" in text or "宛先数 0" in text

    def _ensure_recipient(self, page, scenario_id: str, dest: Path) -> None:
        if not self._userlist_empty(page):
            return
        if not scenario_id:
            raise RuntimeError("シナリオに読者がいないため下書きを作れません。")
        page.goto(
            member_abs(self.settings.myasp_login_url, f"/member/add_user/{scenario_id}/item_id:{scenario_id}"),
            wait_until="networkidle",
            timeout=60000,
        )
        for selector in ("#UserRegist", "#FilterRegiststep"):
            box = page.locator(selector)
            if box.count() and box.is_checked():
                box.uncheck()
        page.locator("#UserName1").fill("自動化")
        page.locator("#UserName2").fill("確認")
        page.locator("#UserMail").fill(self.settings.myasp_user)
        self._shot(page, dest, "02b_add_user.png")
        page.locator('button[name="Submit[save]"]').click()
        page.wait_for_load_state("networkidle", timeout=60000)
        self._shot(page, dest, "02c_after_add_user.png")
        page.goto(
            member_abs(self.settings.myasp_login_url, f"/member/userlist/{scenario_id}/item_id:{scenario_id}"),
            wait_until="networkidle",
            timeout=60000,
        )
        if self._userlist_empty(page):
            raise RuntimeError("シナリオに読者を用意できなかったため下書きを作れません。配信はしていません。")

    def _login(self, page) -> None:
        page.goto(self.settings.myasp_login_url, wait_until="domcontentloaded", timeout=60000)
        page.locator(LOGIN_ID).fill(self.settings.myasp_user)
        page.locator(LOGIN_PASSWORD).fill(self.settings.myasp_password)
        page.locator(LOGIN_SUBMIT).click()
        page.wait_for_load_state("networkidle", timeout=60000)
        if page.locator(LOGIN_ID).count():
            raise RuntimeError("MyASPにログインできませんでした。")

    def _open_userlist(self, page, scenario_name: str, scenario_id: str) -> None:
        if scenario_id:
            page.goto(
                member_abs(self.settings.myasp_login_url, f"/member/userlist/{scenario_id}/item_id:{scenario_id}"),
                wait_until="networkidle",
                timeout=60000,
            )
            return
        page.goto(member_abs(self.settings.myasp_login_url, "/member/item"), wait_until="networkidle", timeout=60000)
        page.get_by_role("link", name=scenario_name, exact=True).first.click()
        page.wait_for_load_state("networkidle", timeout=60000)
        page.goto(member_abs(self.settings.myasp_login_url, "/member/userlist"), wait_until="networkidle", timeout=60000)

    def _assert_not_confirm(self, page) -> None:
        text = page.inner_text("body") or ""
        if "配信する" in text and "確認画面" in (page.title() or ""):
            raise RuntimeError("確認画面に進んでしまいました。配信は実行していません。")
        if page.locator(CONFIRM).count() and "下書き" not in text and "保存" not in text:
            raise RuntimeError("下書き保存の完了を確認できませんでした。配信はしていません。")

    def _fill_body(self, page, text: str) -> str:
        editor = page.frame_locator("iframe.editor2-body-frame").locator("#MailBody")
        editor.wait_for(timeout=30000)
        existing = ""
        try:
            existing = editor.input_value()
        except Exception:
            existing = ""
        hidden = page.locator(BODY_HIDDEN)
        if not existing and hidden.count():
            existing = hidden.input_value()
        payload = merge_body_with_footer(existing, text)
        editor.evaluate(
            """(el, v) => {
                el.value = v;
                el.dispatchEvent(new Event('input', { bubbles: true }));
                el.dispatchEvent(new Event('change', { bubbles: true }));
            }""",
            payload,
        )
        if hidden.count():
            hidden.evaluate(
                """(el, v) => {
                    el.value = v;
                    el.dispatchEvent(new Event('input', { bubbles: true }));
                    el.dispatchEvent(new Event('change', { bubbles: true }));
                }""",
                payload,
            )
        return editor.input_value()
