from moriyama_mail.config import Settings
from moriyama_mail.domain.models import DeliveryMode
from moriyama_mail.domain.safety import SafetyError
from moriyama_mail.intake.request import MyAspPlan
from moriyama_mail.myasp import build_myasp_gateway
from moriyama_mail.myasp.browser import BrowserMyAspGateway, member_abs, merge_body_with_footer, _plain_text
from moriyama_mail.myasp.mock import MockMyAspGateway


def test_plain_text_ignores_crlf():
    assert _plain_text("a\r\n{{DRIVE_SHARE_URL}}\r\nb") == _plain_text("a\n{{DRIVE_SHARE_URL}}\nb")


def test_merge_keeps_unsubscribe_footer():
    existing = "※プライバシーポリシー\nhttps://example.com/\n%unsubscribe%\n"
    merged = merge_body_with_footer(existing, "本文です")
    assert merged.startswith("本文です")
    assert "%unsubscribe%" in merged
    assert "プライバシーポリシー" in merged


def test_merge_keeps_cancelurl_footer():
    existing = "今後の案内が不要な方はこちらから配信停止できます。\n%cancelurl%\n"
    merged = merge_body_with_footer(existing, "本文です")
    assert "本文です" in merged
    assert "%cancelurl%" in merged


def test_merge_does_not_duplicate_footer():
    text = "本文\n%unsubscribe%\n"
    assert merge_body_with_footer("%unsubscribe%", text) == text.rstrip()


def test_member_abs_from_login_url():
    assert member_abs("https://my909p.com/Member/", "/member/userlist/fM6ticMg") == (
        "https://my909p.com/member/userlist/fM6ticMg"
    )


def test_build_gateway_mock_by_default(tmp_path):
    settings = Settings(
        install_dir=tmp_path,
        data_dir=tmp_path,
        secrets_dir=tmp_path / "secrets",
        operator_name="tester",
        test_recipients=(),
        google_drive_mode="mock",
        google_oauth_client_json=None,
        google_token_json=tmp_path / "token.json",
        google_drive_folder_id="",
        drive_link_label="買取案件紹介",
        myasp_mode="mock",
        myasp_login_url="",
        myasp_user="",
        myasp_password="",
        myasp_api_key="",
        myasp_server_url="",
        myasp_mcp_url="",
        myasp_plans=(MyAspPlan(key="test_plan", name="テスト", scenario_id="fM6ticMg"),),
    )
    assert isinstance(build_myasp_gateway(settings), MockMyAspGateway)


def test_build_gateway_live_uses_browser(tmp_path):
    settings = Settings(
        install_dir=tmp_path,
        data_dir=tmp_path,
        secrets_dir=tmp_path / "secrets",
        operator_name="tester",
        test_recipients=(),
        google_drive_mode="mock",
        google_oauth_client_json=None,
        google_token_json=tmp_path / "token.json",
        google_drive_folder_id="",
        drive_link_label="買取案件紹介",
        myasp_mode="live",
        myasp_login_url="https://my909p.com/Member/",
        myasp_user="user@example.com",
        myasp_password="secret",
        myasp_api_key="",
        myasp_server_url="",
        myasp_mcp_url="",
        myasp_plans=(MyAspPlan(key="test_plan", name="テスト", scenario_id="fM6ticMg"),),
    )
    assert isinstance(build_myasp_gateway(settings), BrowserMyAspGateway)


def test_live_send_does_not_send(tmp_path):
    settings = Settings(
        install_dir=tmp_path,
        data_dir=tmp_path,
        secrets_dir=tmp_path / "secrets",
        operator_name="tester",
        test_recipients=(),
        google_drive_mode="mock",
        google_oauth_client_json=None,
        google_token_json=tmp_path / "token.json",
        google_drive_folder_id="",
        drive_link_label="買取案件紹介",
        myasp_mode="live",
        myasp_login_url="https://my909p.com/Member/",
        myasp_user="user@example.com",
        myasp_password="secret",
        myasp_api_key="",
        myasp_server_url="",
        myasp_mcp_url="",
        myasp_plans=(MyAspPlan(key="test_plan", name="テスト", scenario_id="fM6ticMg"),),
    )
    from moriyama_mail.domain.models import Campaign, utc_now, new_campaign_id

    now = utc_now()
    campaign = Campaign(id=new_campaign_id(now), created_at=now, updated_at=now, subject="x", body="y")
    result = BrowserMyAspGateway(settings).send(campaign, DeliveryMode.TEST, ())
    assert not result.ok
    assert "未実装" in result.error
    assert result.target_count == 0


def test_save_myasp_draft_mock(service):
    campaign = service.create_campaign(subject="下書き件名", body="下書き本文", myasp_plan_key="test_plan")
    saved = service.save_myasp_draft(campaign)
    assert saved.subject == "下書き件名"
    assert "{{DRIVE_SHARE_URL}}" in saved.body
    assert "買取案件紹介:" in saved.body
    assert saved.body.find("下書き本文") < saved.body.find("{{DRIVE_SHARE_URL}}")
    audits = service.store.list_audit(saved.id)
    assert any(item["action"] == "myasp_draft" for item in audits)


def test_save_myasp_draft_keeps_placeholder_once(service):
    campaign = service.create_campaign(
        subject="下書き件名",
        body="本文\n\n買取案件紹介: {{DRIVE_SHARE_URL}}\n",
        myasp_plan_key="test_plan",
    )
    saved = service.save_myasp_draft(campaign)
    assert saved.body.count("{{DRIVE_SHARE_URL}}") == 1


def test_save_myasp_draft_requires_subject(service):
    campaign = service.create_campaign(subject="", body="本文", myasp_plan_key="test_plan")
    try:
        service.save_myasp_draft(campaign)
        assert False
    except SafetyError as exc:
        assert "件名" in str(exc)


def test_save_myasp_draft_requires_plan(service):
    campaign = service.create_campaign(subject="件名", body="本文")
    try:
        service.save_myasp_draft(campaign)
        assert False
    except SafetyError as exc:
        assert "プラン" in str(exc)
