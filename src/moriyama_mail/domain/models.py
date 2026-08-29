from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import datetime, timezone
from enum import Enum
import secrets


DRIVE_URL_PLACEHOLDER = "{{DRIVE_SHARE_URL}}"
PRODUCTION_CONFIRM_PHRASE = "本番配信を承認"


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def new_campaign_id(now: datetime | None = None) -> str:
    stamp = (now or utc_now()).strftime("%Y%m%d")
    suffix = secrets.token_hex(2).upper()
    return f"C-{stamp}-{suffix}"


class DeliveryMode(str, Enum):
    TEST = "test"
    PRODUCTION = "production"


class AudienceAction(str, Enum):
    ADD = "add"
    REMOVE = "remove"
    EXCLUDE = "exclude"


class CampaignStatus(str, Enum):
    RECEIVED = "依頼受付"
    MATERIALS_PREPARING = "資料準備中"
    DRIVE_REGISTERED = "Googleドライブ登録済み"
    AUDIENCE_CONFIRMED = "配信対象確認済み"
    MAIL_CREATED = "メール作成済み"
    TEST_SENT = "テスト配信済み"
    AWAITING_CONFIRMATION = "確認待ち"
    PRODUCTION_READY = "本番配信可能"
    PRODUCTION_SENT = "本番配信済み"
    ERROR = "エラー"


@dataclass(frozen=True)
class AudienceEntry:
    email: str
    action: AudienceAction

    def normalized(self) -> AudienceEntry:
        return replace(self, email=self.email.strip().lower())


@dataclass
class AudienceChangeSet:
    """Parsed audience intent. CSV layout is not part of this model."""

    additions: list[str] = field(default_factory=list)
    removals: list[str] = field(default_factory=list)
    exclusions: list[str] = field(default_factory=list)
    skipped: int = 0
    source_name: str = ""

    @property
    def add_count(self) -> int:
        return len(self.additions)

    @property
    def remove_count(self) -> int:
        return len(self.removals)

    @property
    def exclude_count(self) -> int:
        return len(self.exclusions)

    @property
    def target_count(self) -> int:
        excluded = {e.lower() for e in self.exclusions}
        return len([e for e in self.additions if e.lower() not in excluded])


@dataclass
class DeliveryResult:
    ok: bool
    mode: DeliveryMode
    executed_at: datetime
    target_count: int
    exclude_count: int
    message: str = ""
    mock: bool = True
    error: str = ""


@dataclass
class Campaign:
    id: str
    created_at: datetime
    updated_at: datetime
    subject: str = ""
    body: str = ""
    notes: str = ""
    material_path: str = ""
    material_name: str = ""
    drive_file_id: str = ""
    drive_share_url: str = ""
    test_recipients: tuple[str, ...] = ()
    delivery_mode: DeliveryMode = DeliveryMode.TEST
    status: CampaignStatus = CampaignStatus.RECEIVED
    error_message: str = ""
    operator_name: str = ""
    production_locked: bool = False
    test_result: str = ""
    production_result: str = ""
    test_sent_at: datetime | None = None
    production_sent_at: datetime | None = None
    scheduled_at: datetime | None = None
    audience: AudienceChangeSet = field(default_factory=AudienceChangeSet)
    source_channel: str = "manual"

    @property
    def material_selected(self) -> bool:
        return bool(self.material_path or self.material_name)

    @property
    def drive_uploaded(self) -> bool:
        return bool(self.drive_file_id)

    @property
    def share_url_ready(self) -> bool:
        return bool(self.drive_share_url)

    @property
    def audience_loaded(self) -> bool:
        return bool(
            self.audience.additions or self.audience.removals or self.audience.exclusions
        )

    @property
    def mail_ready(self) -> bool:
        return bool(self.subject.strip()) and bool(self.body.strip() or self.drive_share_url)

    @property
    def test_sent(self) -> bool:
        return self.test_sent_at is not None

    @property
    def production_sent(self) -> bool:
        return self.production_sent_at is not None or self.production_locked

    def progress(self) -> dict[str, bool]:
        return {
            "資料選択済み": self.material_selected,
            "資料アップロード済み": self.drive_uploaded,
            "共有URL取得済み": self.share_url_ready,
            "配信対象処理済み": self.audience_loaded,
            "メール作成済み": self.mail_ready,
            "テスト配信済み": self.test_sent,
            "本番配信済み": self.production_sent,
        }


@dataclass(frozen=True)
class ProductionConfirmation:
    campaign_id: str
    subject: str
    delivery_mode: DeliveryMode
    target_count: int
    exclude_count: int
    drive_share_url: str
    production_banner: str
    approved: bool
    typed_phrase: str = ""

    def is_complete(self) -> bool:
        return (
            self.approved
            and self.delivery_mode is DeliveryMode.PRODUCTION
            and self.typed_phrase.strip() == PRODUCTION_CONFIRM_PHRASE
            and bool(self.subject.strip())
            and bool(self.campaign_id)
        )


@dataclass(frozen=True)
class HistoryRecord:
    id: int | None
    executed_at: datetime
    campaign_id: str
    subject: str
    mode: DeliveryMode
    target_count: int
    exclude_count: int
    drive_share_url: str
    success: bool
    error: str
    operator_name: str
    mock: bool
