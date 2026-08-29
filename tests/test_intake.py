from pathlib import Path

from moriyama_mail.domain.safety import SafetyError
from moriyama_mail.intake.request import CampaignRequest


def test_submit_request_requires_plan(service):
    try:
        service.submit_request(CampaignRequest(subject="無プラン", body="本文"))
        assert False
    except SafetyError as exc:
        assert "プラン" in str(exc)


def test_submit_request_selects_plan_and_notifies(service, tmp_path: Path):
    add_csv = tmp_path / "add.csv"
    add_csv.write_text("a@example.com\n", encoding="utf-8")
    exclude_csv = tmp_path / "exclude.csv"
    exclude_csv.write_text("a@example.com\n", encoding="utf-8")
    campaign, message = service.submit_request(
        CampaignRequest(
            subject="専用フォーム依頼",
            body="本文です",
            myasp_plan_key="plan2",
            additions_csv=add_csv,
            exclusions_csv=exclude_csv,
        )
    )
    assert campaign.source_channel == "dedicated_form"
    assert campaign.myasp_plan_key == "plan2"
    assert campaign.myasp_plan_name == "プラン2"
    assert campaign.audience.add_count == 1
    assert campaign.audience.exclude_count == 1
    assert campaign.audience.target_count == 0
    assert campaign.send_timing == "scheduled"
    assert "fake notify" in message


def test_production_without_plan_is_blocked_after_confirmation(service):
    campaign, _ = service.create_campaign(subject="プラン未選択", body="本文")
    try:
        service.confirm_and_send_production(campaign, "本番配信を承認", True)
        assert False
    except SafetyError as exc:
        assert "プラン" in str(exc)
