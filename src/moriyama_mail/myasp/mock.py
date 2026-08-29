from __future__ import annotations

from moriyama_mail.domain.models import (
    AudienceChangeSet,
    Campaign,
    DeliveryMode,
    DeliveryResult,
    utc_now,
)
from moriyama_mail.myasp.gateway import MyAspMailDraft


class MockMyAspGateway:
    """Phase 1 stand-in. Does not log in to MyASP or send to subscribers."""

    def apply_audience(self, campaign: Campaign, changes: AudienceChangeSet) -> str:
        return (
            f"mock: audience queued for {campaign.id} "
            f"(add={changes.add_count}, remove={changes.remove_count}, exclude={changes.exclude_count})"
        )

    def create_mail(self, campaign: Campaign) -> MyAspMailDraft:
        return MyAspMailDraft(subject=campaign.subject, body=campaign.body, mock=True)

    def send(self, campaign: Campaign, mode: DeliveryMode, recipients: tuple[str, ...]) -> DeliveryResult:
        if mode is DeliveryMode.PRODUCTION:
            target_count = campaign.audience.target_count
            message = (
                "MyASP本番配信は第1段階では実行しません（モック）。"
                "確認と承認の記録のみ保存しました。"
            )
            return DeliveryResult(
                ok=True,
                mode=mode,
                executed_at=utc_now(),
                target_count=target_count,
                exclude_count=campaign.audience.exclude_count,
                message=message,
                mock=True,
            )
        return DeliveryResult(
            ok=True,
            mode=mode,
            executed_at=utc_now(),
            target_count=len(recipients),
            exclude_count=0,
            message="テスト配信をモックとして記録しました（SMTP未設定のため実送信なし）。",
            mock=True,
        )
