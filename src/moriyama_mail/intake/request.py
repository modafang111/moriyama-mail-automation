from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class MyAspPlan:
    key: str
    name: str
    scenario_id: str = ""

    def label(self) -> str:
        return self.name.strip() or self.key


@dataclass
class CampaignRequest:
    """Normalized intake payload. Delivery processing does not depend on form widgets."""

    subject: str = ""
    body: str = ""
    notes: str = ""
    myasp_plan_key: str = ""
    material_path: Path | None = None
    additions_csv: Path | None = None
    exclusions_csv: Path | None = None
    email_column: str | None = None
    source_channel: str = "dedicated_form"
