from pathlib import Path

from moriyama_mail.domain.models import DRIVE_URL_PLACEHOLDER, Campaign, utc_now
from moriyama_mail.domain.placeholders import (
    assemble_reader_mail,
    body_with_share_url,
    draft_reader_body,
    prepare_reader_body_for_draft,
)
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


def test_draft_reader_body_marks_url_place_without_upload():
    drafted = draft_reader_body("資料をご確認ください。")
    assert "資料をご確認ください。" in drafted
    assert "{{DRIVE_SHARE_URL}}" in drafted
    assert "買取案件紹介:" in drafted


def test_prepare_draft_body_is_idempotent_with_signature():
    first = prepare_reader_body_for_draft(
        "資料をご確認ください。",
        signature="盛山英幸\nバイリンク株式会社",
    )
    second = prepare_reader_body_for_draft(
        first,
        signature="盛山英幸\nバイリンク株式会社",
    )
    assert first == second
    assert first.count("{{DRIVE_SHARE_URL}}") == 1
    assert first.count("盛山英幸") == 1


def test_prepare_draft_body_does_not_duplicate_crlf_signature():
    signature = "盛山英幸（090-7340-5252）\nバイリンク株式会社　大阪本店"
    first = prepare_reader_body_for_draft(
        "宜しくお願いいたします。\r\n",
        signature=signature,
    )
    crlf_saved = first.replace("\n", "\r\n")
    second = prepare_reader_body_for_draft(
        crlf_saved,
        signature=signature,
    )
    assert second.count("盛山英幸（090-7340-5252）") == 1
    assert second.count("{{DRIVE_SHARE_URL}}") == 1


def test_assemble_puts_share_url_before_signature():
    mail = assemble_reader_mail(
        "是非、ご情報提供宜しくお願いいたします。",
        "盛山英幸\nバイリンク株式会社",
    )
    url_at = mail.find("{{DRIVE_SHARE_URL}}")
    sig_at = mail.find("盛山英幸")
    assert url_at != -1 and sig_at != -1
    assert url_at < sig_at


def test_drive_upload_sets_readonly_share_url(service, tmp_path: Path):
    pdf = tmp_path / "sample.pdf"
    pdf.write_bytes(b"%PDF-1.4 mock")
    campaign = service.create_campaign(subject="資料", body=f"リンク {DRIVE_URL_PLACEHOLDER}")
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
