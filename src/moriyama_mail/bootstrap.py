from __future__ import annotations

from pathlib import Path

from moriyama_mail.config import Settings, load_settings
from moriyama_mail.drive import build_drive_gateway
from moriyama_mail.myasp import build_myasp_gateway
from moriyama_mail.paths import database_path
from moriyama_mail.privacy import configure_logging
from moriyama_mail.services.campaign_service import CampaignService
from moriyama_mail.storage.store import Store


def build_service(settings: Settings | None = None, db_path: Path | None = None) -> CampaignService:
    configure_logging()
    settings = settings or load_settings()
    store = Store(db_path or database_path())
    return CampaignService(
        settings=settings,
        store=store,
        drive=build_drive_gateway(settings),
        myasp=build_myasp_gateway(settings),
    )
