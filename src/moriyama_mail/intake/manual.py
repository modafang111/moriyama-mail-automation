from __future__ import annotations

from typing import Protocol

from moriyama_mail.domain.models import Campaign


class IntakeAdapter(Protocol):
    """Request intake is separate from delivery processing."""

    channel_name: str

    def describe(self) -> str:
        ...


class ManualIntakeAdapter:
    channel_name = "manual"

    def describe(self) -> str:
        return "手動登録（依頼方法が決まるまでの暫定）"
