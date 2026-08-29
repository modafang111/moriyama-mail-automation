from pathlib import Path

from moriyama_mail.domain.models import AudienceAction, DeliveryMode
from moriyama_mail.domain.safety import SafetyError, default_delivery_mode
from moriyama_mail.privacy import mask_email, redact_text


def test_default_mode_is_test():
    assert default_delivery_mode() is DeliveryMode.TEST


def test_create_campaign_defaults_to_test_and_notifies(service):
    campaign, message = service.create_campaign(subject="件名A")
    assert campaign.delivery_mode is DeliveryMode.TEST
    assert campaign.status.value == "依頼受付"
    assert "fake notify" in message
    assert campaign.id in service.fake_notifier.sent_requests


def test_production_without_confirmation_is_blocked(service):
    campaign, _ = service.create_campaign(subject="本番テスト", body="本文")
    try:
        service.execute_delivery(campaign, DeliveryMode.PRODUCTION)
        assert False, "should have blocked"
    except SafetyError as exc:
        assert "最終確認" in str(exc)


def test_production_wrong_phrase_is_blocked(service):
    campaign, _ = service.create_campaign(subject="本番テスト", body="本文")
    try:
        service.confirm_and_send_production(campaign, "OK", True)
        assert False
    except SafetyError:
        pass
    assert campaign.production_sent_at is None
    assert service.list_history() == []


def test_production_requires_explicit_approval(service):
    campaign, _ = service.create_campaign(subject="本番テスト", body="本文", myasp_plan_key="plan1")
    campaign, result = service.confirm_and_send_production(campaign, "本番配信を承認", True)
    assert result.ok
    assert result.mock
    assert campaign.production_locked
    assert campaign.status.value == "本番配信済み"
    history = service.list_history()
    assert len(history) == 1
    assert history[0].mode is DeliveryMode.PRODUCTION
    assert history[0].subject == "本番テスト"


def test_duplicate_production_is_blocked(service):
    campaign, _ = service.create_campaign(subject="本番テスト", body="本文", myasp_plan_key="plan1")
    service.confirm_and_send_production(campaign, "本番配信を承認", True)
    campaign = service.get(campaign.id)
    try:
        service.confirm_and_send_production(campaign, "本番配信を承認", True)
        assert False
    except SafetyError as exc:
        assert "本番配信済み" in str(exc)
    assert len(service.list_history()) == 1


def test_test_delivery_uses_only_configured_recipients(service, tmp_path: Path):
    campaign, _ = service.create_campaign(subject="テスト", body="本文")
    csv_path = tmp_path / "audience.csv"
    csv_path.write_text("mail\ncustomer1@example.com\ncustomer2@example.com\n", encoding="utf-8")
    service.load_audience_file(campaign, csv_path, AudienceAction.ADD, "mail")
    campaign = service.get(campaign.id)
    campaign, result = service.execute_delivery(campaign, DeliveryMode.TEST)
    assert result.target_count == 1
    assert service.fake_notifier.sent_tests[0][1] == ("confirm@example.com",)
    assert campaign.audience.add_count == 2


def test_preview_contains_required_production_fields(service):
    campaign, _ = service.create_campaign(subject="確認画面", body="本文", myasp_plan_key="plan1")
    preview = service.preview_delivery(campaign, DeliveryMode.PRODUCTION)
    for key in ("subject", "delivery_mode", "target_count", "exclude_count", "drive_share_url", "production_banner"):
        assert key in preview
    assert "予約配信" in str(preview["production_banner"])
    assert "即時" in str(preview["production_banner"])
    assert preview["send_timing"] == "scheduled"
    assert "今回の配信だけ" in str(preview["exclude_meaning"])
