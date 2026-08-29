from moriyama_mail.domain.models import AudienceAction, DeliveryMode


def test_history_does_not_store_audience_addresses(service, tmp_path):
    campaign = service.create_campaign(subject="履歴", body="本文")
    csv_path = tmp_path / "people.csv"
    csv_path.write_text("mail\nsecret.person@example.com\n", encoding="utf-8")
    service.load_audience_file(campaign, csv_path, AudienceAction.ADD, "mail")
    campaign = service.get(campaign.id)
    service.execute_delivery(campaign, DeliveryMode.TEST)
    history = service.list_history()
    assert history
    blob = " ".join(
        [
            history[0].subject,
            history[0].error,
            history[0].campaign_id,
            history[0].drive_share_url,
        ]
    )
    assert "secret.person@example.com" not in blob
    audits = service.store.list_audit(campaign.id)
    joined = " ".join(item["detail"] for item in audits)
    assert "secret.person@example.com" not in joined
    assert history[0].operator_name == "tester"
