import base64
from pathlib import Path

from moriyama_mail.intake.wordpress import payload_to_request
from moriyama_mail.intake.request import CampaignRequest


def test_wordpress_payload_becomes_campaign(service, tmp_path: Path):
    csv_bytes = b"mail\nwp@example.com\n"
    payload = {
        "id": "20260101-abc",
        "myasp_plan_key": "test_plan",
        "subject": "WPからの依頼",
        "body": "本文",
        "notes": "備考",
        "additions_csv": {
            "filename": "people.csv",
            "content_base64": base64.b64encode(csv_bytes).decode("ascii"),
        },
    }
    request = payload_to_request(payload, tmp_path / "uploads")
    assert request.source_channel == "wordpress_form"
    campaign = service.submit_request(request)
    assert campaign.source_channel == "wordpress_form"
    assert campaign.subject == "WPからの依頼"
    assert campaign.myasp_plan_name == "テストプラン"
    assert campaign.audience.add_count == 1


def test_wordpress_import_empty_token_is_blocked(service):
    from moriyama_mail.domain.safety import SafetyError

    try:
        service.import_wordpress_requests()
        assert False
    except SafetyError as exc:
        assert "TOKEN" in str(exc)
