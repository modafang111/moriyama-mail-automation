from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from moriyama_mail.domain.models import AudienceChangeSet, Campaign, DeliveryMode, DeliveryResult


@dataclass(frozen=True)
class MyAspMailDraft:
    subject: str
    body: str
    scenario_id: str = ""
    mock: bool = True


class MyAspGateway(Protocol):
    def apply_audience(self, campaign: Campaign, changes: AudienceChangeSet) -> str:
        ...

    def create_mail(self, campaign: Campaign) -> MyAspMailDraft:
        ...

    def send(self, campaign: Campaign, mode: DeliveryMode, recipients: tuple[str, ...]) -> DeliveryResult:
        ...
