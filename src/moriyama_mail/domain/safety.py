from __future__ import annotations

from moriyama_mail.domain.models import (
    Campaign,
    DeliveryMode,
    PRODUCTION_CONFIRM_PHRASE,
    ProductionConfirmation,
)


class SafetyError(Exception):
    """Raised when a delivery would violate the anti-misdelivery rules."""


def default_delivery_mode() -> DeliveryMode:
    return DeliveryMode.TEST


def build_production_confirmation(campaign: Campaign, typed_phrase: str, approved: bool) -> ProductionConfirmation:
    return ProductionConfirmation(
        campaign_id=campaign.id,
        subject=campaign.subject,
        delivery_mode=DeliveryMode.PRODUCTION,
        target_count=campaign.audience.target_count,
        exclude_count=campaign.audience.exclude_count,
        drive_share_url=campaign.drive_share_url,
        production_banner="これは本番の予約配信です。即時配信は行いません。MyASPの配信対象者へ送られます。",
        approved=approved,
        typed_phrase=typed_phrase,
    )


def reader_material_issues(campaign: Campaign) -> list[str]:
    url = (campaign.drive_share_url or "").strip()
    if not url:
        return ["読者が見る資料の共有URLがありません。Driveへ上げてから本文へ入れてください。"]
    if url not in (campaign.body or ""):
        return ["本文に共有URLが入っていません。読者が資料を開けません。「本文へ挿入」を押してください。"]
    return []


def preflight_issues(campaign: Campaign, mode: DeliveryMode) -> list[str]:
    issues: list[str] = []
    if not campaign.subject.strip():
        issues.append("メール件名が未入力です。")
    issues.extend(reader_material_issues(campaign))
    if mode is DeliveryMode.PRODUCTION:
        if not campaign.myasp_plan_key:
            issues.append("MyASPプランが未選択です。")
        if campaign.audience.target_count < 1:
            issues.append("配信対象が0件です。宛先ファイルを読み込んでから実行してください。")
        if campaign.production_locked or campaign.production_sent:
            issues.append("この案件は本番配信済みです。同じ案件の再配信はできません。")
    return issues


def assert_ready_to_send(campaign: Campaign, mode: DeliveryMode) -> None:
    issues = preflight_issues(campaign, mode)
    if issues:
        raise SafetyError("配信前チェックで止めています。\n" + "\n".join(f"・{item}" for item in issues))


def assert_can_prepare(campaign: Campaign, mode: DeliveryMode) -> None:
    if mode not in (DeliveryMode.TEST, DeliveryMode.PRODUCTION):
        raise SafetyError("配信モードが選択されていません。")
    if not campaign.subject.strip():
        raise SafetyError("メール件名が未入力です。")


def assert_test_recipients(recipients: tuple[str, ...]) -> None:
    if not recipients:
        raise SafetyError("テスト配信先が設定されていません。")


def assert_production_allowed(campaign: Campaign, confirmation: ProductionConfirmation | None) -> None:
    if confirmation is None or not confirmation.is_complete():
        raise SafetyError("本番配信には最終確認と「本番配信を承認」の入力が必要です。")
    if confirmation.campaign_id != campaign.id:
        raise SafetyError("確認画面の案件が現在の案件と一致しません。")
    if confirmation.subject != campaign.subject:
        raise SafetyError("確認画面の件名が現在の件名と一致しません。")
    if campaign.production_locked or campaign.production_sent:
        raise SafetyError("この案件は本番配信済みです。同じ案件の再配信はできません。")
    if confirmation.typed_phrase.strip() != PRODUCTION_CONFIRM_PHRASE:
        raise SafetyError("確認フレーズが正しくありません。")


def production_replay_warning(campaign: Campaign) -> str | None:
    if campaign.production_locked or campaign.production_sent:
        return (
            f"案件 {campaign.id} は本番配信済みです。"
            "同じ案件を再度本番配信することは、誤配信防止のため禁止しています。"
        )
    return None
