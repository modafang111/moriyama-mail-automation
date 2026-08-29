from __future__ import annotations

from typing import Protocol


class IntakeAdapter(Protocol):
    """Request intake is separate from delivery processing."""

    channel_name: str

    def describe(self) -> str:
        ...


class DedicatedFormIntake:
    channel_name = "dedicated_form"

    def describe(self) -> str:
        return "ウェブ専用フォーム"
