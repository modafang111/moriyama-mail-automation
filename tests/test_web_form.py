from io import BytesIO

from moriyama_mail.intake.webapp import create_app


def test_customer_browser_form_shows_placeholder_plans(service):
    client = create_app(service).test_client()
    response = client.get("/")
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "メルマガ配信の依頼" in text
    assert "テストプラン" in text
    assert "本番プラン" in text
    assert "担当者へ依頼を送る" in text
    assert "ウェブの専用依頼フォームです" in text
    assert "担当者へ届きます" in text


def test_customer_browser_form_posts_to_operator(service):
    client = create_app(service).test_client()
    response = client.post(
        "/request",
        data={
            "myasp_plan_key": "test_plan",
            "subject": "顧客からの依頼",
            "body": "本文を送ります",
            "notes": "確認お願いします",
            "additions_csv": (BytesIO(b"mail\nnew@example.com\n"), "people.csv"),
        },
    )
    assert response.status_code == 200
    text = response.get_data(as_text=True)
    assert "依頼を受け付けました" in text
    assert "new@example.com" not in text
    assert "メールを送信" not in text
    assert "通知メール" not in text
    campaigns = service.list_campaigns()
    assert campaigns
    assert campaigns[0].subject == "顧客からの依頼"
    assert campaigns[0].myasp_plan_name == "テストプラン"
    assert campaigns[0].source_channel == "dedicated_form"


def test_customer_form_requires_plan(service):
    client = create_app(service).test_client()
    response = client.post(
        "/request",
        data={"subject": "件名", "body": "本文"},
    )
    assert response.status_code == 400
    assert "プラン" in response.get_data(as_text=True)
