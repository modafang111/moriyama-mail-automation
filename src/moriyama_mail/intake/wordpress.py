from __future__ import annotations

import base64
import json
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urljoin
from urllib.request import Request, urlopen
from uuid import uuid4

from moriyama_mail.domain.safety import SafetyError
from moriyama_mail.intake.request import CampaignRequest


def _decode_file(payload: object, dest_dir: Path, prefix: str) -> Path | None:
    if not isinstance(payload, dict):
        return None
    name = str(payload.get("filename") or "upload.bin")
    raw = str(payload.get("content_base64") or "")
    if not raw:
        return None
    dest_dir.mkdir(parents=True, exist_ok=True)
    safe = "".join(ch for ch in Path(name).name if ch.isalnum() or ch in "._-") or "upload.bin"
    path = dest_dir / f"{prefix}_{uuid4().hex[:8]}_{safe}"
    path.write_bytes(base64.b64decode(raw))
    return path


def payload_to_request(payload: dict, upload_dir: Path) -> CampaignRequest:
    return CampaignRequest(
        subject=str(payload.get("subject") or "").strip(),
        body=str(payload.get("body") or "").strip(),
        notes=str(payload.get("notes") or "").strip(),
        myasp_plan_key=str(payload.get("myasp_plan_key") or "").strip(),
        material_path=_decode_file(payload.get("material"), upload_dir, "material"),
        additions_csv=_decode_file(payload.get("additions_csv"), upload_dir, "add"),
        exclusions_csv=_decode_file(payload.get("exclusions_csv"), upload_dir, "exclude"),
        source_channel="wordpress_form",
    )


class WordPressIntakeClient:
    def __init__(self, form_url: str, token: str) -> None:
        self.form_url = (form_url or "").strip()
        self.token = (token or "").strip()

    def _fetch_endpoint(self) -> str:
        if not self.form_url:
            raise SafetyError("WordPress専用フォームのURLが設定されていません。")
        if not self.token:
            raise SafetyError("WORDPRESS_INTAKE_TOKEN を .env に入れてください。")
        base = self.form_url if self.form_url.endswith("/") else self.form_url + "/"
        return urljoin(base, "fetch.php")

    def fetch_pending(self) -> list[dict]:
        url = f"{self._fetch_endpoint()}?{urlencode({'token': self.token})}"
        try:
            with urlopen(Request(url, method="GET"), timeout=30) as response:
                body = json.loads(response.read().decode("utf-8"))
        except HTTPError as exc:
            raise SafetyError(f"WordPressからの取り込みに失敗しました（HTTP {exc.code}）。") from exc
        except URLError as exc:
            raise SafetyError("WordPressのフォームに接続できませんでした。") from exc
        except json.JSONDecodeError as exc:
            raise SafetyError("WordPressからの応答が読み取れませんでした。") from exc
        if not isinstance(body, dict) or not body.get("ok"):
            raise SafetyError(str((body or {}).get("error") or "WordPressからの取り込みに失敗しました。"))
        items = body.get("requests") or []
        if not isinstance(items, list):
            return []
        return [item for item in items if isinstance(item, dict)]

    def mark_imported(self, request_ids: list[str]) -> None:
        data = urlencode(
            {
                "token": self.token,
                "action": "imported",
                "ids": ",".join(request_ids),
            }
        ).encode("utf-8")
        request = Request(self._fetch_endpoint(), data=data, method="POST")
        try:
            with urlopen(request, timeout=30) as response:
                json.loads(response.read().decode("utf-8"))
        except (HTTPError, URLError, json.JSONDecodeError):
            return
