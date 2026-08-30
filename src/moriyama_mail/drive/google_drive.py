from __future__ import annotations

from pathlib import Path

from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

from moriyama_mail.config import Settings
from moriyama_mail.drive.gateway import DriveUploadResult

SCOPES = ["https://www.googleapis.com/auth/drive.file"]


class GoogleDriveGateway:
    def __init__(self, settings: Settings) -> None:
        if not settings.google_oauth_client_json:
            raise RuntimeError("GOOGLE_OAUTH_CLIENT_JSON が設定されていません。")
        self._settings = settings

    def upload_readonly(self, path: Path, folder_id: str = "") -> DriveUploadResult:
        if not path.is_file():
            raise FileNotFoundError(str(path))
        service = self._service()
        metadata: dict[str, object] = {"name": path.name}
        target_folder = folder_id or self._settings.google_drive_folder_id
        if target_folder:
            metadata["parents"] = [target_folder]
        media = MediaFileUpload(str(path), resumable=True)
        created = (
            service.files()
            .create(body=metadata, media_body=media, fields="id,name,webViewLink")
            .execute()
        )
        file_id = created["id"]
        service.permissions().create(
            fileId=file_id,
            body={"type": "anyone", "role": "reader", "allowFileDiscovery": False},
            fields="id",
        ).execute()
        meta = (
            service.files()
            .get(fileId=file_id, fields="id,name,webViewLink")
            .execute()
        )
        url = meta.get("webViewLink") or f"https://drive.google.com/file/d/{file_id}/view?usp=sharing"
        return DriveUploadResult(
            file_id=file_id,
            share_url=url,
            filename=meta.get("name") or path.name,
            mock=False,
        )

    def _service(self):
        creds = None
        token_path = self._settings.google_token_json
        client_path = self._settings.google_oauth_client_json
        assert client_path is not None
        if token_path and token_path.exists():
            creds = Credentials.from_authorized_user_file(str(token_path), SCOPES)
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(str(client_path), SCOPES)
                creds = flow.run_local_server(port=0)
            if token_path:
                token_path.parent.mkdir(parents=True, exist_ok=True)
                token_path.write_text(creds.to_json(), encoding="utf-8")
        return build("drive", "v3", credentials=creds, cache_discovery=False)
