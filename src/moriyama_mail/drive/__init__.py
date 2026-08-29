from moriyama_mail.config import Settings
from moriyama_mail.drive.gateway import DriveGateway
from moriyama_mail.drive.mock import MockDriveGateway


def build_drive_gateway(settings: Settings) -> DriveGateway:
    if settings.drive_live:
        from moriyama_mail.drive.google_drive import GoogleDriveGateway

        return GoogleDriveGateway(settings)
    return MockDriveGateway(settings.data_dir / "drive_mock")
