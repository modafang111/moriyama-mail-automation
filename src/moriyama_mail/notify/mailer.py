from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Protocol

from moriyama_mail.config import Settings
from moriyama_mail.domain.models import Campaign
from moriyama_mail.privacy import mask_email


class Notifier(Protocol):
    def notify_request_received(self, campaign: Campaign) -> str:
        ...

    def send_test_mail(self, campaign: Campaign, recipients: tuple[str, ...]) -> str:
        ...


class NullNotifier:
    def notify_request_received(self, campaign: Campaign) -> str:
        return "通知メールは未設定のため送信していません。"

    def send_test_mail(self, campaign: Campaign, recipients: tuple[str, ...]) -> str:
        masked = ", ".join(mask_email(item) for item in recipients)
        return f"SMTP未設定のためテストメールは記録のみです。宛先: {masked}"


class SmtpNotifier:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def notify_request_received(self, campaign: Campaign) -> str:
        if not self._settings.notify_enabled:
            return "通知は無効です。"
        if not self._settings.notify_to:
            return "NOTIFY_TO が未設定です。"
        subject = f"[依頼受付] {campaign.id} {campaign.subject or '（件名未設定）'}"
        body = (
            "新しい配信依頼（案件）が登録されました。\n\n"
            f"案件ID: {campaign.id}\n"
            f"作成日時(UTC): {campaign.created_at.isoformat()}\n"
            f"件名: {campaign.subject or '（未設定）'}\n"
            f"資料: {campaign.material_name or '（未選択）'}\n"
            f"受付経路: {campaign.source_channel}\n\n"
            "配信対象者のメールアドレス一覧はこの通知には含めていません。\n"
        )
        self._send(self._settings.notify_to, subject, body)
        return f"依頼通知を送信しました: {mask_email(self._settings.notify_to)}"

    def send_test_mail(self, campaign: Campaign, recipients: tuple[str, ...]) -> str:
        if not recipients:
            raise ValueError("テスト配信先が空です。")
        subject = f"[テスト配信] {campaign.subject}"
        body = campaign.body or "(本文なし)"
        for recipient in recipients:
            self._send(recipient, subject, body)
        return f"テストメールを {len(recipients)} 件送信しました。"

    def _send(self, to_addr: str, subject: str, body: str) -> None:
        s = self._settings
        message = EmailMessage()
        message["Subject"] = subject
        message["From"] = s.smtp_from
        message["To"] = to_addr
        message.set_content(body)
        with smtplib.SMTP(s.smtp_host, s.smtp_port, timeout=30) as smtp:
            if s.smtp_use_tls:
                smtp.starttls()
            if s.smtp_user:
                smtp.login(s.smtp_user, s.smtp_password)
            smtp.send_message(message)


def build_notifier(settings: Settings) -> Notifier:
    if settings.smtp_ready:
        return SmtpNotifier(settings)
    return NullNotifier()
