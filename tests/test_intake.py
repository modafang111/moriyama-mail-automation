from dataclasses import fields
from pathlib import Path

from moriyama_mail.config import Settings
from moriyama_mail.domain.safety import SafetyError
from moriyama_mail.intake.request import CampaignRequest
from moriyama_mail.domain.placeholders import draft_reader_body
from moriyama_mail.notify.mailer import format_request_notice, notify_campaign_registered


def test_settings_do_not_include_smtp_or_notify():
    names = {item.name.lower() for item in fields(Settings)}
    assert not any("smtp" in name or name.startswith("notify") for name in names)


def test_notify_body_omits_counts_and_audience():
    title, body = format_request_notice(
        request_id="20260830-abc",
        subject="確認",
        plan="テストプラン",
        notes="なし",
        created_at="2026-08-30",
        message_body="こんにちは。資料をご確認ください。",
        has_material=True,
        has_additions=True,
        signature="盛山英幸\nバイリンク株式会社",
    )
    assert title.startswith("[メルマガ依頼]")
    assert "20260830-abc" in body
    assert "■ 1. 盛山さんが書いた本文（修正前）" in body
    assert "■ 2. 読者へ送る本文（修正後）" in body
    assert "こんにちは。資料をご確認ください。" in body
    before, after = body.split("■ 2. 読者へ送る本文（修正後）", 1)
    assert "盛山英幸" in before
    assert "{{DRIVE_SHARE_URL}}" not in before
    assert "盛山英幸" in after
    assert "{{DRIVE_SHARE_URL}}" in after
    assert after.find("{{DRIVE_SHARE_URL}}") < after.find("盛山英幸")
    assert "買取案件紹介:" in body
    assert "まだ（次の工程でDriveへ上げたあと入ります）" in body
    assert "配信用資料" in body and "このメールに添付しています。" in body
    assert "宛先のファイル" in body
    assert "集計" not in body
    assert "同期成功" not in body
    assert "対象件数" not in body
    assert "example.com" not in body
    assert "配信対象" not in body


def test_notify_helper_is_skipped_under_pytest(service):
    campaign = service.create_campaign(subject="通知なし", body="本文")
    assert notify_campaign_registered(campaign) is None


def test_notify_uses_shared_notify_note_with_attachment(monkeypatch):
    from moriyama_mail.notify import mailer

    calls: list[tuple] = []

    class FakeNotify:
        @staticmethod
        def notify_note(project, subject, body, **kwargs):
            calls.append((project, subject, body, kwargs.get("attachments")))
            return True

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(mailer, "_shared_notify", lambda: FakeNotify)
    assert (
        mailer.notify_request_received(
            request_id="abc",
            subject="件名",
            attachments=[("shiryo_a.pdf", b"%PDF")],
        )
        is True
    )
    assert calls[0][0] == "moriyama-mail-automation"
    assert calls[0][1] == "[メルマガ依頼] 件名"
    assert "集計" not in calls[0][2]
    assert calls[0][3] == [("shiryo_a.pdf", b"%PDF")]


def test_notify_does_not_send_when_additions_format_fails(monkeypatch):
    from moriyama_mail.notify import mailer

    called = []

    class FakeNotify:
        @staticmethod
        def notify_note(*args, **kwargs):
            called.append(True)
            return True

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(mailer, "_shared_notify", lambda: FakeNotify)
    assert (
        mailer.notify_request_received(
            request_id="abc",
            subject="件名",
            attachments=[("atesaki_people.csv", b"mail\nnew@example.com\n")],
        )
        is False
    )
    assert called == []


def test_notify_sends_when_additions_format_ok(monkeypatch):
    from moriyama_mail.notify import mailer
    from tests.additions_fixtures import fixture_path

    calls: list[tuple] = []

    class FakeNotify:
        @staticmethod
        def notify_note(project, subject, body, **kwargs):
            calls.append((project, subject, body, kwargs.get("attachments")))
            return True

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(mailer, "_shared_notify", lambda: FakeNotify)
    files = [("atesaki_ユーザーリスト_sample.csv", fixture_path("01_通る_ShiftJIS.csv").read_bytes())]
    assert mailer.notify_request_received(request_id="ok1", subject="件名", attachments=files) is True
    assert calls
    assert calls[0][3] == files
    assert "書式は送信前に確認しています" in calls[0][2]


def test_collects_material_and_additions_attachments():
    from moriyama_mail.notify.mailer import collect_request_attachments
    import base64

    files = collect_request_attachments(
        material={"filename": "資料.pdf", "content_base64": base64.b64encode(b"pdf").decode("ascii")},
        additions={"filename": "people.csv", "content_base64": base64.b64encode(b"mail\n").decode("ascii")},
    )
    names = [name for name, _data in files]
    assert any(name.startswith("shiryo_") and name.endswith(".pdf") for name in names)
    assert any(name.startswith("atesaki_") and name.endswith(".csv") for name in names)


def test_submit_request_requires_plan(service):
    try:
        service.submit_request(CampaignRequest(subject="無プラン", body="本文"))
        assert False
    except SafetyError as exc:
        assert "プラン" in str(exc)


def test_submit_request_selects_plan(service, tmp_path: Path):
    add_csv = tmp_path / "add.csv"
    add_csv.write_text("a@example.com\n", encoding="utf-8")
    campaign = service.submit_request(
        CampaignRequest(
            subject="専用フォーム依頼",
            body="本文です",
            myasp_plan_key="production_plan",
            additions_csv=add_csv,
        )
    )
    assert campaign.source_channel == "dedicated_form"
    assert campaign.myasp_plan_key == "production_plan"
    assert campaign.myasp_plan_name == "本番プラン"
    assert campaign.audience.add_count == 1
    assert campaign.audience.exclude_count == 0
    assert campaign.audience.target_count == 1
    assert campaign.send_timing == "scheduled"
    assert "{{DRIVE_SHARE_URL}}" in campaign.body
    assert campaign.body.find("本文です") < campaign.body.find("{{DRIVE_SHARE_URL}}")
    assert any(item["action"] == "myasp_draft" for item in service.store.list_audit(campaign.id))
    assert not campaign.error_message


def test_submit_request_drafts_subject_and_revised_body(service):
    original = "こんにちは。資料をご確認ください。"
    signature = "盛山英幸\nバイリンク株式会社"
    _, notice = format_request_notice(
        request_id="x",
        subject="買取案件のご案内",
        plan="テストプラン",
        message_body=original,
        signature=signature,
    )
    revised = draft_reader_body(original, "", service.settings.drive_link_label, signature)
    assert revised in notice
    campaign = service.submit_request(
        CampaignRequest(
            subject="買取案件のご案内",
            body=original,
            signature=signature,
            myasp_plan_key="test_plan",
        )
    )
    assert campaign.subject == "買取案件のご案内"
    assert campaign.body == revised
    assert "{{DRIVE_SHARE_URL}}" in campaign.body
    assert campaign.body.find(original) < campaign.body.find("{{DRIVE_SHARE_URL}}")
    assert campaign.body.find("{{DRIVE_SHARE_URL}}") < campaign.body.find("盛山英幸")


def test_production_without_plan_is_blocked_after_confirmation(service):
    campaign = service.create_campaign(subject="プラン未選択", body="本文")
    campaign.drive_share_url = "https://drive.google.com/file/d/x/view"
    campaign.body = f"本文\n{campaign.drive_share_url}\n"
    try:
        service.confirm_and_send_production(campaign, "本番配信を承認", True)
        assert False
    except SafetyError as exc:
        assert "プラン" in str(exc)
