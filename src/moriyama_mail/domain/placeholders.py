from __future__ import annotations

from moriyama_mail.domain.models import DRIVE_URL_PLACEHOLDER, Campaign


def _plain_newlines(text: str) -> str:
    return (text or "").replace("\r\n", "\n").replace("\r", "\n")


def signature_already_present(body: str, signature: str) -> bool:
    sig = _plain_newlines(signature).strip()
    text = _plain_newlines(body)
    if not sig:
        return False
    if sig in text:
        return True
    first = sig.split("\n", 1)[0].strip()
    return bool(first) and first in text


def apply_share_url(body: str, url: str, link_label: str = "") -> str:
    text = body or ""
    share = (url or "").strip()
    if not share:
        return text
    if DRIVE_URL_PLACEHOLDER in text:
        return text.replace(DRIVE_URL_PLACEHOLDER, share)
    if share in text:
        return text
    label = link_label.strip()
    line = f"{label}: {share}" if label else share
    if text.strip():
        return f"{text.rstrip()}\n\n{line}\n"
    return f"{line}\n"


def body_with_share_url(campaign: Campaign, link_label: str = "") -> str:
    return apply_share_url(campaign.body, campaign.drive_share_url.strip(), link_label)


def assemble_signed_body(body: str, signature: str = "") -> str:
    mid = (body or "").rstrip()
    sig = (signature or "").strip()
    if sig and signature_already_present(mid, sig):
        sig = ""
    if mid and sig:
        return f"{mid}\n\n{sig}\n"
    if sig:
        return f"{sig}\n"
    return mid or "（なし）"


def assemble_reader_mail(
    body: str,
    signature: str = "",
    share_url: str = "",
    link_label: str = "買取案件紹介",
) -> str:
    """Body, then share URL, then signature. Uses a placeholder until a real URL exists."""
    marker = (share_url or "").strip() or DRIVE_URL_PLACEHOLDER
    mid = apply_share_url(body or "", marker, link_label).rstrip()
    sig = (signature or "").strip()
    if sig and signature_already_present(mid, sig):
        sig = ""
    if mid and sig:
        return f"{mid}\n\n{sig}\n"
    if sig:
        return f"{sig}\n"
    return mid or "（なし）"


def draft_reader_body(
    original: str,
    share_url: str = "",
    link_label: str = "買取案件紹介",
    signature: str = "",
) -> str:
    return assemble_reader_mail(original, signature, share_url, link_label)


def prepare_reader_body_for_draft(
    body: str,
    *,
    share_url: str = "",
    signature: str = "",
    link_label: str = "買取案件紹介",
) -> str:
    """Assemble the reader mail. Keeps {{DRIVE_SHARE_URL}} until a real URL exists."""
    text = body or ""
    sig = (signature or "").strip()
    share = (share_url or "").strip()
    already_has_url = DRIVE_URL_PLACEHOLDER in text or (share and share in text)
    already_has_sig = not sig or signature_already_present(text, sig)
    if already_has_url and already_has_sig:
        return text if text.endswith("\n") else f"{text}\n"
    if already_has_sig:
        sig = ""
    return assemble_reader_mail(text, sig, share, link_label)


def contains_placeholder(body: str) -> bool:
    return DRIVE_URL_PLACEHOLDER in (body or "")
