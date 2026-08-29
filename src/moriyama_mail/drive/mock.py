from __future__ import annotations

import shutil
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

from moriyama_mail.drive.gateway import DriveUploadResult
from moriyama_mail.paths import data_dir


class MockDriveGateway:
    """Used until Google credentials exist. Does not contact Google."""

    def __init__(self, dest_dir: Path | None = None) -> None:
        self._dest_dir = dest_dir

    def upload_readonly(self, path: Path, folder_id: str = "") -> DriveUploadResult:
        if not path.is_file():
            raise FileNotFoundError(str(path))
        dest_dir = self._dest_dir or (data_dir() / "drive_mock")
        dest_dir.mkdir(parents=True, exist_ok=True)
        file_id = uuid4().hex
        dest = dest_dir / f"{file_id}_{path.name}"
        shutil.copy2(path, dest)
        url = f"https://drive.google.com/file/d/mock-{file_id}/view?usp=sharing"
        if folder_id:
            url += f"&folder={quote(folder_id)}"
        return DriveUploadResult(
            file_id=f"mock-{file_id}",
            share_url=url,
            filename=path.name,
            mock=True,
        )
