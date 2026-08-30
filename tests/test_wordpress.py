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
        "signature": "盛山英幸\nバイリンク株式会社",
        "reader_body": "本文\n\n買取案件紹介: {{DRIVE_SHARE_URL}}\n\n盛山英幸\nバイリンク株式会社\n",
        "additions_csv": {
            "filename": "people.csv",
            "content_base64": base64.b64encode(csv_bytes).decode("ascii"),
        },
    }
    request = payload_to_request(payload, tmp_path / "uploads")
    assert request.source_channel == "wordpress_form"
    assert request.signature.startswith("盛山英幸")
    campaign = service.submit_request(request)
    assert campaign.source_channel == "wordpress_form"
    assert campaign.subject == "WPからの依頼"
    assert campaign.myasp_plan_name == "テストプラン"
    assert campaign.audience.add_count == 1
    assert campaign.body == request.reader_body or campaign.body == request.reader_body.rstrip() + "\n"
    assert "{{DRIVE_SHARE_URL}}" in campaign.body
    assert campaign.body.find("本文") < campaign.body.find("{{DRIVE_SHARE_URL}}")
    assert campaign.body.find("{{DRIVE_SHARE_URL}}") < campaign.body.find("盛山英幸")
    assert any(item["action"] == "myasp_draft" for item in service.store.list_audit(campaign.id))
    assert not campaign.error_message


def test_wordpress_fetch_php_exposes_logs_action():
    text = (Path(__file__).resolve().parents[1] / "web" / "wordpress-form" / "fetch.php").read_text(
        encoding="utf-8"
    )
    assert "action === 'logs'" in text
    assert "action === 'item'" in text
    assert "intake_attach_files" in text
    assert "data/logs" in text.replace("\\", "/") or "logs/" in text


def test_wordpress_import_empty_token_is_blocked(service):
    from moriyama_mail.domain.safety import SafetyError

    try:
        service.import_wordpress_requests()
        assert False
    except SafetyError as exc:
        assert "TOKEN" in str(exc)
