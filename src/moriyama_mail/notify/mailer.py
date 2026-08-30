"""Notify via D:\\dev\\cloud-agent-sync\\notify.py (same helper as line-stamp-auto)."""

from __future__ import annotations

import base64
import os
import sys
from pathlib import Path

from moriyama_mail.domain.placeholders import assemble_signed_body, draft_reader_body

SHARED_NOTIFY_DIR = Path(r"D:\dev\cloud-agent-sync")
PROJECT_NAME = "moriyama-mail-automation"


def _under_pytest() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def _shared_notify():
    root = str(SHARED_NOTIFY_DIR)
    if root not in sys.path:
        sys.path.insert(0, root)
    import notify as notify_mail

    return notify_mail


def shared_notify_settings() -> dict[str, str]:
    settings = _shared_notify().home_settings()
    if not settings.ready():
        raise RuntimeError("cloud-agent-sync notify.local.json is not ready")
    return {
        "to": settings.to_email,
        "from": settings.smtp_user,
        "password": settings.smtp_password,
        "host": settings.smtp_host,
        "port": str(settings.smtp_port),
    }


def _safe_filename(name: str) -> str:
    raw = Path(name or "material.bin").name
    cleaned = "".join(ch for ch in raw if ch.isalnum() or ch in "._-")
    return cleaned or "material.bin"


def attachment_from_payload(payload: object, *, kind: str) -> tuple[str, bytes] | None:
    if not isinstance(payload, dict):
        return None
    raw = str(payload.get("content_base64") or "")
    if not raw:
        return None
    name = _safe_filename(str(payload.get("filename") or f"{kind}.bin"))
    return f"{kind}_{name}", base64.b64decode(raw)


def attachment_from_path(path: str | Path | None, *, kind: str) -> tuple[str, bytes] | None:
    if not path:
        return None
    file_path = Path(path)
    if not file_path.is_file():
        return None
    return f"{kind}_{_safe_filename(file_path.name)}", file_path.read_bytes()


def collect_request_attachments(
    *,
    material: object | str | Path | None = None,
    additions: object | str | Path | None = None,
) -> list[tuple[str, bytes]]:
    files: list[tuple[str, bytes]] = []
    for value, kind, from_payload in (
        (material, "shiryo", isinstance(material, dict)),
        (additions, "atesaki", isinstance(additions, dict)),
    ):
        if value is None:
            continue
        attached = (
            attachment_from_payload(value, kind=kind)
            if from_payload
            else attachment_from_path(value, kind=kind)
        )
        if attached:
            files.append(attached)
    return files


def format_request_notice(
    *,
    request_id: str = "",
    subject: str = "",
    plan: str = "",
    notes: str = "",
    created_at: str = "",
    message_body: str = "",
    has_material: bool = False,
    has_additions: bool = False,
    share_url: str = "",
    link_label: str = "買取案件紹介",
    signature: str = "",
) -> tuple[str, str]:
    title = f"[メルマガ依頼] {subject or request_id or '新規依頼'}"
    original = assemble_signed_body(message_body, signature)
    drafted = draft_reader_body(message_body, share_url, link_label, signature)
    url_line = (share_url or "").strip() or "まだ（次の工程でDriveへ上げたあと入ります）"
    rule = "------------------------------------------------------------"
    lines = [
        "メルマガ配信の依頼が届きました。",
        "宛先ファイルの書式は送信前に確認しています。ここから読者へは送っていません。",
        "",
        rule,
        "■ 依頼の内容",
        rule,
        f"受付番号　{request_id or '（なし）'}",
        f"件名　　　{subject or '（なし）'}",
        f"プラン　　{plan or '（なし）'}",
        f"受付日時　{created_at or '（なし）'}",
        f"備考　　　{notes or 'なし'}",
        "",
        rule,
        "■ 1. 盛山さんが書いた本文（修正前）",
        "本文に署名を付けた形です。共有URLはまだ入っていません。",
        rule,
        original,
        "",
        rule,
        "■ 2. 読者へ送る本文（修正後）",
        "上の本文に、共有URLの位置と署名を付けた形です。",
        f"共有URL　{url_line}",
        rule,
        drafted,
        "",
        rule,
        "■ 添付ファイル",
        rule,
        "配信用資料　　　　" + ("このメールに添付しています。" if has_material else "ありません。"),
        "宛先のファイル　　" + ("このメールに添付しています。" if has_additions else "ありません。"),
        "フォーム　https://wordpress-123.com/mail-request/",
    ]
    return title, "\n".join(lines)


def additions_attachment_error(attachments: list[tuple[str, bytes]]) -> str | None:
    from moriyama_mail.audience.myasp_list import additions_format_error

    for name, data in attachments:
        if not name.startswith("atesaki_"):
            continue
        error = additions_format_error(data, name)
        if error:
            return error
    return None


def notify_request_received(
    *,
    request_id: str = "",
    subject: str = "",
    plan: str = "",
    notes: str = "",
    created_at: str = "",
    message_body: str = "",
    attachments: list[tuple[str, bytes]] | None = None,
    has_material: bool | None = None,
    has_additions: bool | None = None,
    signature: str | None = None,
) -> bool:
    incoming = list(attachments or [])
    format_error = additions_attachment_error(incoming)
    if format_error:
        return False
    files = [item for item in incoming if item[1]]
    names = [name for name, _data in files]
    if _under_pytest():
        return True
    if signature is None:
        try:
            from moriyama_mail.config import load_settings

            signature = load_settings().mail_signature
        except Exception:
            signature = ""
    title, body = format_request_notice(
        request_id=request_id,
        subject=subject,
        plan=plan,
        notes=notes,
        created_at=created_at,
        message_body=message_body,
        has_material=bool(has_material) if has_material is not None else any(n.startswith("shiryo_") for n in names),
        has_additions=bool(has_additions) if has_additions is not None else any(n.startswith("atesaki_") for n in names),
        signature=signature,
    )
    notify_mail = _shared_notify()
    return bool(
        notify_mail.notify_note(
            PROJECT_NAME,
            title,
            body,
            attachments=files or None,
        )
    )


def notify_campaign_registered(campaign=None, request=None) -> None:
    if campaign is None:
        return
    files = collect_request_attachments(
        material=getattr(campaign, "material_path", "") or "",
        additions=getattr(request, "additions_csv", None) if request is not None else None,
    )
    notify_request_received(
        request_id=getattr(campaign, "id", "") or "",
        subject=getattr(campaign, "subject", "") or "",
        plan=getattr(campaign, "myasp_plan_name", "") or getattr(campaign, "myasp_plan_key", "") or "",
        notes=getattr(campaign, "notes", "") or "",
        created_at=str(getattr(campaign, "created_at", "") or ""),
        message_body=getattr(campaign, "body", "") or "",
        attachments=files,
        signature=getattr(request, "signature", "") or "",
    )


def notify_wordpress_payload(payload: dict) -> bool:
    plan = str(payload.get("myasp_plan_key") or "")
    plan_label = {
        "production_plan": "本番プラン",
        "test_plan": "テストプラン",
    }.get(plan, plan)
    files = collect_request_attachments(
        material=payload.get("material"),
        additions=payload.get("additions_csv"),
    )
    return notify_request_received(
        request_id=str(payload.get("id") or ""),
        subject=str(payload.get("subject") or ""),
        plan=plan_label,
        notes=str(payload.get("notes") or ""),
        created_at=str(payload.get("created_at") or ""),
        message_body=str(payload.get("body") or ""),
        attachments=files,
        signature=str(payload.get("signature") or ""),
    )
