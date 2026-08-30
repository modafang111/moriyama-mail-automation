from io import BytesIO

from moriyama_mail.intake.webapp import create_app
from tests.additions_fixtures import fixture_path


def _pdf():
    return (BytesIO(b"%PDF-1.4 mock"), "shiryo.pdf")


def test_customer_browser_form_shows_placeholder_plans(service):
    client = create_app(service).test_client()
    response = client.get("/")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "メルマガ配信の依頼" in text
    assert "テストプラン" in text
    assert "本番プラン" in text
    assert 'value="test_plan"' in text and "checked" in text
    assert "送信" in text
    assert "担当者への依頼窓口" in text
    assert "送る前に" in text
    assert "CSV（.csv）だけ" in text
    assert "追加や修正" in text
    assert "今回だけ送らない" not in text
    assert "プレビュー（読者へ届く形・共有URL入り）" in text
    assert 'name="signature"' in text
    assert "署名は次の欄で編集" in text


def test_customer_browser_form_rejects_non_myasp_list(service):
    client = create_app(service).test_client()
    response = client.post(
        "/request",
        data={
            "myasp_plan_key": "test_plan",
            "subject": "事前チェック",
            "body": "本文を送ります",
            "material": _pdf(),
            "additions_csv": (BytesIO(fixture_path("06_止まる_メールだけの一覧.csv").read_bytes()), "people.csv"),
        },
    )
    assert response.status_code == 400
    text = response.get_data(as_text=True)
    assert "MyASPのユーザーリストの形式ではありません" in text
    assert "追加や修正" in text
    assert "理由:" in text
    assert "a@example.com" not in text
    assert service.list_campaigns() == []


def test_customer_browser_form_rejects_non_csv_additions(service):
    client = create_app(service).test_client()
    path = fixture_path("15_止まる_拡張子がtxt.txt")
    response = client.post(
        "/request",
        data={
            "myasp_plan_key": "test_plan",
            "subject": "事前チェック",
            "body": "本文を送ります",
            "material": _pdf(),
            "additions_csv": (BytesIO(path.read_bytes()), path.name),
        },
    )
    assert response.status_code == 400
    text = response.get_data(as_text=True)
    assert "CSV（.csv）だけ" in text
    assert service.list_campaigns() == []


def test_customer_browser_form_posts_to_operator(service):
    client = create_app(service).test_client()
    path = fixture_path("01_通る_ShiftJIS.csv")
    response = client.post(
        "/request",
        data={
            "myasp_plan_key": "test_plan",
            "subject": "事前チェック",
            "body": "本文を送ります",
            "notes": "確認お願いします",
            "material": _pdf(),
            "additions_csv": (BytesIO(path.read_bytes()), path.name),
        },
    )
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "依頼を受け付けました" in text
    assert "reader@example.com" not in text
    campaigns = service.list_campaigns()
    assert campaigns
    assert campaigns[0].subject == "事前チェック"
    assert campaigns[0].myasp_plan_name == "テストプラン"
    assert campaigns[0].source_channel == "dedicated_form"
    assert "{{DRIVE_SHARE_URL}}" in campaigns[0].body
    assert any(item["action"] == "myasp_draft" for item in service.store.list_audit(campaigns[0].id))


def test_customer_form_requires_plan(service):
    client = create_app(service).test_client()
    response = client.post(
        "/request",
        data={"subject": "件名", "body": "本文"},
    )
    assert response.status_code == 400
    assert "プラン" in response.get_data(as_text=True)
