from __future__ import annotations

from moriyama_mail.domain.models import DRIVE_URL_PLACEHOLDER, Campaign


def body_with_share_url(campaign: Campaign, link_label: str = "") -> str:
    url = campaign.drive_share_url.strip()
    body = campaign.body
    if not url:
        return body
    if DRIVE_URL_PLACEHOLDER in body:
        return body.replace(DRIVE_URL_PLACEHOLDER, url)
    label = link_label.strip()
    line = f"{label}: {url}" if label else url
    if url in body:
        return body
    if body.strip():
        return f"{body.rstrip()}\n\n{line}\n"
    return f"{line}\n"


def contains_placeholder(body: str) -> bool:
    return DRIVE_URL_PLACEHOLDER in (body or "")
