from pathlib import Path

from moriyama_mail.domain.models import DRIVE_URL_PLACEHOLDER, Campaign, utc_now
from moriyama_mail.domain.placeholders import body_with_share_url
from moriyama_mail.privacy import mask_email, redact_text


def test_placeholder_replaced_with_url():
    campaign = Campaign(
        id="C-1",
        created_at=utc_now(),
        updated_at=utc_now(),
        body=f"詳細は {DRIVE_URL_PLACEHOLDER} です。",
        drive_share_url="https://drive.google.com/file/d/abc/view",
    )
    assert "https://drive.google.com/file/d/abc/view" in body_with_share_url(campaign)


def test_drive_upload_sets_readonly_share_url(service, tmp_path: Path):
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4 mock")
    campaign, _ = service.create_campaign(subject="資料", body=f"リンク {DRIVE_URL_PLACEHOLDER}")
    service.set_material(campaign, pdf)
    campaign = service.upload_to_drive(campaign)
    assert campaign.drive_share_url
    assert campaign.drive_file_id.startswith("mock-")
    assert campaign.drive_share_url in campaign.body
    assert campaign.progress()["資料アップロード済み"]
    assert campaign.progress()["共有URL取得済み"]
    assert campaign.progress()["メール作成済み"]


def test_mask_email_and_redact_logs():
    assert mask_email("customer@example.com") == "c***@example.com"
    assert "customer@example.com" not in redact_text("failed for customer@example.com")
