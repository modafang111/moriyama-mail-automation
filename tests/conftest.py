from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

import pytest

from moriyama_mail.config import Settings
from moriyama_mail.drive.mock import MockDriveGateway
from moriyama_mail.intake.request import MyAspPlan
from moriyama_mail.myasp.mock import MockMyAspGateway
from moriyama_mail.services.campaign_service import CampaignService
from moriyama_mail.storage.store import Store


@dataclass
class FakeNotifier:
    sent_requests: list
    sent_tests: list

    def notify_request_received(self, campaign):
        self.sent_requests.append(campaign.id)
        return "fake notify"

    def send_test_mail(self, campaign, recipients):
        self.sent_tests.append((campaign.id, recipients))
        return f"sent {len(recipients)}"


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        install_dir=tmp_path,
        data_dir=tmp_path,
        secrets_dir=tmp_path / "secrets",
        operator_name="tester",
        test_recipients=("confirm@example.com",),
        notify_enabled=True,
        notify_to=("operator@example.com", "modafang111@gmail.com"),
        smtp_host="",
        smtp_port=587,
        smtp_user="",
        smtp_password="",
        smtp_from="",
        smtp_use_tls=True,
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
        myasp_plans=(
            MyAspPlan(key="plan1", name="プラン1", scenario_id=""),
            MyAspPlan(key="plan2", name="プラン2", scenario_id=""),
        ),
        production_is_immediate=False,
    )


@pytest.fixture
def service(tmp_path: Path) -> CampaignService:
    settings = make_settings(tmp_path)
    notifier = FakeNotifier(sent_requests=[], sent_tests=[])
    svc = CampaignService(
        settings=settings,
        store=Store(tmp_path / "test.sqlite3"),
        drive=MockDriveGateway(tmp_path / "drive_mock"),
        myasp=MockMyAspGateway(),
        notifier=notifier,
    )
    svc.fake_notifier = notifier  # type: ignore[attr-defined]
    return svc
