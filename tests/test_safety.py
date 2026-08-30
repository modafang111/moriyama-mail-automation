from pathlib import Path

from moriyama_mail.domain.models import AudienceAction, DeliveryMode
from moriyama_mail.domain.safety import SafetyError, default_delivery_mode, preflight_issues
from moriyama_mail.privacy import mask_email, redact_text

SHARE_URL = "https://drive.google.com/file/d/testdoc/view"


def _ready_campaign(service, tmp_path: Path, *, subject="本番テスト", body="本文です", plan="test_plan"):
    campaign = service.create_campaign(subject=subject, body=body, myasp_plan_key=plan)
    campaign.drive_share_url = SHARE_URL
    campaign.body = f"{body}\n\n買取案件紹介: {SHARE_URL}\n"
    csv_path = tmp_path / "audience.csv"
    csv_path.write_text("mail\nreader@example.com\n", encoding="utf-8")
    service.load_audience_file(campaign, csv_path, AudienceAction.ADD, "mail")
    return service.get(campaign.id)


def test_default_mode_is_test():
    assert default_delivery_mode() is DeliveryMode.TEST


def test_create_campaign_defaults_to_test(service):
    campaign = service.create_campaign(subject="件名A")
    assert campaign.delivery_mode is DeliveryMode.TEST
    assert campaign.status.value == "依頼受付"


def test_production_without_confirmation_is_blocked(service, tmp_path: Path):
    campaign = _ready_campaign(service, tmp_path)
    try:
        service.execute_delivery(campaign, DeliveryMode.PRODUCTION)
        assert False, "should have blocked"
    except SafetyError as exc:
        assert "最終確認" in str(exc)


def test_production_wrong_phrase_is_blocked(service, tmp_path: Path):
    campaign = _ready_campaign(service, tmp_path)
    try:
        service.confirm_and_send_production(campaign, "OK", True)
        assert False
    except SafetyError:
        pass
    assert campaign.production_sent_at is None
    assert service.list_history() == []


def test_preflight_requires_share_url_in_body(service):
    campaign = service.create_campaign(subject="本番テスト", body="本文だけ", myasp_plan_key="test_plan")
    issues = preflight_issues(campaign, DeliveryMode.PRODUCTION)
    assert any("共有URL" in item for item in issues)
    try:
        service.confirm_and_send_production(campaign, "本番配信を承認", True)
        assert False
    except SafetyError as exc:
        assert "共有URL" in str(exc)


def test_production_requires_explicit_approval(service, tmp_path: Path):
    campaign = _ready_campaign(service, tmp_path)
    campaign, result = service.confirm_and_send_production(campaign, "本番配信を承認", True)
    assert result.ok
    assert result.mock
    assert campaign.production_locked
    assert campaign.status.value == "本番配信済み"
    history = service.list_history()
    assert len(history) == 1
    assert history[0].mode is DeliveryMode.PRODUCTION
    assert history[0].subject == "本番テスト"


def test_duplicate_production_is_blocked(service, tmp_path: Path):
    campaign = _ready_campaign(service, tmp_path)
    service.confirm_and_send_production(campaign, "本番配信を承認", True)
    campaign = service.get(campaign.id)
    try:
        service.confirm_and_send_production(campaign, "本番配信を承認", True)
        assert False
    except SafetyError as exc:
        assert "本番配信済み" in str(exc)
    assert len(service.list_history()) == 1


def test_test_delivery_uses_only_configured_recipients(service, tmp_path: Path):
    campaign = service.create_campaign(subject="テスト", body="本文")
    campaign.drive_share_url = SHARE_URL
    campaign.body = f"本文\n{SHARE_URL}\n"
    csv_path = tmp_path / "audience.csv"
    csv_path.write_text("mail\ncustomer1@example.com\ncustomer2@example.com\n", encoding="utf-8")
    service.load_audience_file(campaign, csv_path, AudienceAction.ADD, "mail")
    campaign = service.get(campaign.id)
    campaign, result = service.execute_delivery(campaign, DeliveryMode.TEST)
    assert result.target_count == 1
    assert campaign.audience.add_count == 2


def test_preview_contains_required_production_fields(service):
    campaign = service.create_campaign(subject="確認画面", body="本文", myasp_plan_key="test_plan")
    preview = service.preview_delivery(campaign, DeliveryMode.PRODUCTION)
    for key in ("subject", "delivery_mode", "target_count", "exclude_count", "drive_share_url", "production_banner"):
        assert key in preview
    assert "予約配信" in str(preview["production_banner"])
    assert "即時" in str(preview["production_banner"])
    assert preview["send_timing"] == "scheduled"
    assert "今回の配信だけ" in str(preview["exclude_meaning"])
    assert "preflight_issues" in preview
    assert any("共有URL" in item for item in preview["preflight_issues"])
