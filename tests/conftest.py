from __future__ import annotations

from pathlib import Path

import pytest

from moriyama_mail.config import Settings
from moriyama_mail.drive.mock import MockDriveGateway
from moriyama_mail.intake.request import MyAspPlan
from moriyama_mail.myasp.mock import MockMyAspGateway
from moriyama_mail.services.campaign_service import CampaignService
from moriyama_mail.storage.store import Store


def make_settings(tmp_path: Path) -> Settings:
    return Settings(
        install_dir=tmp_path,
        data_dir=tmp_path,
        secrets_dir=tmp_path / "secrets",
        operator_name="tester",
        test_recipients=("confirm@example.com",),
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
            MyAspPlan(key="test_plan", name="テストプラン", scenario_id=""),
            MyAspPlan(key="production_plan", name="本番プラン", scenario_id=""),
        ),
        production_is_immediate=False,
        intake_host="127.0.0.1",
        intake_port=8787,
        wordpress_form_url="https://wordpress-123.com/mail-request/",
        wordpress_intake_token="",
    )


@pytest.fixture
def service(tmp_path: Path) -> CampaignService:
    settings = make_settings(tmp_path)
    return CampaignService(
        settings=settings,
        store=Store(tmp_path / "test.sqlite3"),
        drive=MockDriveGateway(tmp_path / "drive_mock"),
        myasp=MockMyAspGateway(),
    )
