from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Protocol


@dataclass(frozen=True)
class DriveUploadResult:
    file_id: str
    share_url: str
    filename: str
    mock: bool


class DriveGateway(Protocol):
    def upload_readonly(self, path: Path, folder_id: str = "") -> DriveUploadResult:
        ...
