from __future__ import annotations

from pathlib import Path

from moriyama_mail.audience.parser import AudienceParser, ColumnMapping, merge_changes
from moriyama_mail.config import Settings
from moriyama_mail.domain.models import (
    AudienceAction,
    AudienceChangeSet,
    Campaign,
    DeliveryMode,
    DeliveryResult,
    HistoryRecord,
    ProductionConfirmation,
    EXCLUDE_MEANING,
    PRODUCTION_SEND_TIMING,
    new_campaign_id,
    utc_now,
)
from moriyama_mail.domain.placeholders import body_with_share_url
from moriyama_mail.domain.safety import (
    SafetyError,
    assert_can_prepare,
    assert_production_allowed,
    assert_test_recipients,
    build_production_confirmation,
    default_delivery_mode,
    production_replay_warning,
)
from moriyama_mail.domain.status import apply_derived_status
from moriyama_mail.drive.gateway import DriveGateway
from moriyama_mail.intake.form import DedicatedFormIntake
from moriyama_mail.intake.request import CampaignRequest
from moriyama_mail.myasp.gateway import MyAspGateway
from moriyama_mail.notify.mailer import Notifier, NullNotifier
from moriyama_mail.privacy import redact_text
from moriyama_mail.storage.store import Store


class CampaignService:
    def __init__(
        self,
        settings: Settings,
        store: Store,
        drive: DriveGateway,
        myasp: MyAspGateway,
        notifier: Notifier,
        parser: AudienceParser | None = None,
    ) -> None:
        self.settings = settings
        self.store = store
        self.drive = drive
        self.myasp = myasp
        self.notifier = notifier
        self.parser = parser or AudienceParser()
        self.intake = DedicatedFormIntake()

    def create_campaign(
        self,
        subject: str = "",
        body: str = "",
        notes: str = "",
        myasp_plan_key: str = "",
        notify: bool = True,
    ) -> tuple[Campaign, str]:
        plan = self.settings.plan_by_key(myasp_plan_key) if myasp_plan_key else None
        now = utc_now()
        campaign = Campaign(
            id=new_campaign_id(now),
            created_at=now,
            updated_at=now,
            subject=subject,
            body=body,
            notes=notes,
            test_recipients=self.settings.test_recipients,
            delivery_mode=default_delivery_mode(),
            operator_name=self.settings.operator_name,
            source_channel=self.intake.channel_name,
            myasp_plan_key=plan.key if plan else myasp_plan_key,
            myasp_plan_name=plan.label() if plan else "",
            send_timing=PRODUCTION_SEND_TIMING,
        )
        apply_derived_status(campaign)
        self.store.save_campaign(campaign)
        self.store.add_audit(campaign.id, "create", campaign.operator_name, self.intake.describe())
        notify_message = "通知は送信していません。"
        if notify:
            try:
                notify_message = self.notifier.notify_request_received(campaign)
            except Exception as exc:
                notify_message = f"依頼通知の送信に失敗しました: {redact_text(str(exc))}"
            self.store.add_audit(campaign.id, "notify", campaign.operator_name, redact_text(notify_message))
        return campaign, notify_message

    def submit_request(self, request: CampaignRequest) -> tuple[Campaign, str]:
        if not request.myasp_plan_key:
            raise SafetyError("依頼時に MyASP プランを選んでください。")
        if self.settings.plan_by_key(request.myasp_plan_key) is None:
            raise SafetyError("選択した MyASP プランが設定にありません。")
        campaign, notify_message = self.create_campaign(
            subject=request.subject,
            body=request.body,
            notes=request.notes,
            myasp_plan_key=request.myasp_plan_key,
            notify=False,
        )
        if request.material_path:
            campaign = self.set_material(campaign, request.material_path)
        if request.additions_csv:
            campaign = self.load_audience_file(
                campaign, request.additions_csv, AudienceAction.ADD, request.email_column
            )
        if request.exclusions_csv:
            campaign = self.load_audience_file(
                campaign, request.exclusions_csv, AudienceAction.EXCLUDE, request.email_column
            )
        try:
            notify_message = self.notifier.notify_request_received(campaign)
        except Exception as exc:
            notify_message = f"依頼通知の送信に失敗しました: {redact_text(str(exc))}"
        self.store.add_audit(campaign.id, "notify", campaign.operator_name, redact_text(notify_message))
        return campaign, notify_message

    def list_campaigns(self) -> list[Campaign]:
        return self.store.list_campaigns()

    def get(self, campaign_id: str) -> Campaign:
        campaign = self.store.get_campaign(campaign_id)
        if campaign is None:
            raise KeyError(campaign_id)
        return campaign

    def save_content(
        self,
        campaign: Campaign,
        subject: str,
        body: str,
        notes: str,
        mode: DeliveryMode,
        myasp_plan_key: str | None = None,
    ) -> Campaign:
        if campaign.production_locked and mode is DeliveryMode.PRODUCTION:
            pass
        campaign.subject = subject
        campaign.body = body
        campaign.notes = notes
        campaign.delivery_mode = mode
        if myasp_plan_key is not None:
            plan = self.settings.plan_by_key(myasp_plan_key)
            campaign.myasp_plan_key = myasp_plan_key
            campaign.myasp_plan_name = plan.label() if plan else ""
        campaign.error_message = ""
        self.store.save_campaign(campaign)
        self.store.add_audit(campaign.id, "save_content", campaign.operator_name)
        return campaign

    def set_material(self, campaign: Campaign, path: Path) -> Campaign:
        campaign.material_path = str(path)
        campaign.material_name = path.name
        campaign.error_message = ""
        self.store.save_campaign(campaign)
        self.store.add_audit(campaign.id, "select_material", campaign.operator_name, path.name)
        return campaign

    def upload_to_drive(self, campaign: Campaign) -> Campaign:
        if not campaign.material_path:
            raise SafetyError("配信用資料が選択されていません。")
        result = self.drive.upload_readonly(Path(campaign.material_path), self.settings.google_drive_folder_id)
        campaign.drive_file_id = result.file_id
        campaign.drive_share_url = result.share_url
        campaign.body = body_with_share_url(campaign, self.settings.drive_link_label)
        campaign.error_message = ""
        self.store.save_campaign(campaign)
        self.store.add_audit(
            campaign.id,
            "drive_upload",
            campaign.operator_name,
            f"mock={result.mock} file={result.filename}",
        )
        return campaign

    def insert_share_url(self, campaign: Campaign) -> Campaign:
        if not campaign.drive_share_url:
            raise SafetyError("共有URLがまだありません。")
        campaign.body = body_with_share_url(campaign, self.settings.drive_link_label)
        self.store.save_campaign(campaign)
        return campaign

    def load_audience_file(
        self,
        campaign: Campaign,
        path: Path,
        action: AudienceAction,
        email_column: str | None = None,
    ) -> Campaign:
        parsed = self.parser.parse_file(path, action, ColumnMapping(email_column=email_column))
        campaign.audience = merge_changes(campaign.audience, parsed)
        summary = self.myasp.apply_audience(campaign, parsed)
        campaign.error_message = ""
        self.store.save_campaign(campaign)
        self.store.add_audit(
            campaign.id,
            f"audience_{action.value}",
            campaign.operator_name,
            f"count={len(getattr(parsed, {AudienceAction.ADD: 'additions', AudienceAction.REMOVE: 'removals', AudienceAction.EXCLUDE: 'exclusions'}[action]))} skipped={parsed.skipped} {summary}",
        )
        return campaign

    def replace_audience(self, campaign: Campaign, changes: AudienceChangeSet) -> Campaign:
        campaign.audience = changes
        summary = self.myasp.apply_audience(campaign, changes)
        self.store.save_campaign(campaign)
        self.store.add_audit(campaign.id, "audience_replace", campaign.operator_name, summary)
        return campaign

    def preview_delivery(self, campaign: Campaign, mode: DeliveryMode) -> dict[str, object]:
        assert_can_prepare(campaign, mode)
        warning = production_replay_warning(campaign) if mode is DeliveryMode.PRODUCTION else None
        if mode is DeliveryMode.TEST:
            recipients = campaign.test_recipients or self.settings.test_recipients
            target_count = len(recipients)
            exclude_count = 0
        else:
            target_count = campaign.audience.target_count
            exclude_count = campaign.audience.exclude_count
        return {
            "campaign_id": campaign.id,
            "subject": campaign.subject,
            "delivery_mode": mode,
            "target_count": target_count,
            "exclude_count": exclude_count,
            "drive_share_url": campaign.drive_share_url,
            "myasp_plan": campaign.myasp_plan_name or campaign.myasp_plan_key,
            "send_timing": campaign.send_timing,
            "exclude_meaning": EXCLUDE_MEANING,
            "production_banner": "これは本番の予約配信です。即時配信は行いません。MyASPの配信対象者へ送られます。"
            if mode is DeliveryMode.PRODUCTION
            else "テスト配信です。確認用アドレスにのみ送ります。",
            "replay_warning": warning,
            "test_recipient_count": len(campaign.test_recipients or self.settings.test_recipients),
            "body_preview": campaign.body[:500],
        }

    def execute_delivery(
        self,
        campaign: Campaign,
        mode: DeliveryMode,
        confirmation: ProductionConfirmation | None = None,
    ) -> tuple[Campaign, DeliveryResult]:
        assert_can_prepare(campaign, mode)
        try:
            if mode is DeliveryMode.TEST:
                recipients = campaign.test_recipients or self.settings.test_recipients
                assert_test_recipients(recipients)
                result = self._send_test(campaign, recipients)
            else:
                warning = production_replay_warning(campaign)
                if warning:
                    raise SafetyError(warning)
                assert_production_allowed(campaign, confirmation)
                if not campaign.myasp_plan_key:
                    raise SafetyError("本番配信の前に MyASP プランを選択してください。")
                if self.settings.production_is_immediate:
                    raise SafetyError("即時の本番配信は現在使わない設定です。")
                result = self.myasp.send(campaign, DeliveryMode.PRODUCTION, ())
                campaign.production_sent_at = result.executed_at
                campaign.production_locked = True
                campaign.production_result = result.message
            campaign.delivery_mode = mode
            campaign.error_message = "" if result.ok else result.error
        except Exception as exc:
            if isinstance(exc, SafetyError):
                raise
            campaign.error_message = redact_text(str(exc))
            result = DeliveryResult(
                ok=False,
                mode=mode,
                executed_at=utc_now(),
                target_count=0,
                exclude_count=campaign.audience.exclude_count,
                error=campaign.error_message,
                mock=True,
            )
        self._record_history(campaign, mode, result)
        self.store.save_campaign(campaign)
        return campaign, result

    def confirm_and_send_production(self, campaign: Campaign, typed_phrase: str, approved: bool) -> tuple[Campaign, DeliveryResult]:
        confirmation = build_production_confirmation(campaign, typed_phrase, approved)
        return self.execute_delivery(campaign, DeliveryMode.PRODUCTION, confirmation)

    def list_history(self, campaign_id: str | None = None) -> list[HistoryRecord]:
        return self.store.list_history(campaign_id)

    def _send_test(self, campaign: Campaign, recipients: tuple[str, ...]) -> DeliveryResult:
        smtp_message = ""
        mock = True
        try:
            smtp_message = self.notifier.send_test_mail(campaign, recipients)
            mock = isinstance(self.notifier, NullNotifier) or not self.settings.smtp_ready
        except Exception as exc:
            smtp_message = redact_text(str(exc))
        myasp_result = self.myasp.send(campaign, DeliveryMode.TEST, recipients)
        combined = f"{smtp_message} / {myasp_result.message}"
        campaign.test_sent_at = utc_now()
        campaign.test_result = combined
        return DeliveryResult(
            ok=True,
            mode=DeliveryMode.TEST,
            executed_at=campaign.test_sent_at,
            target_count=len(recipients),
            exclude_count=0,
            message=combined,
            mock=mock or myasp_result.mock,
        )

    def _record_history(self, campaign: Campaign, mode: DeliveryMode, result: DeliveryResult) -> None:
        if mode is DeliveryMode.TEST:
            target_count = result.target_count
            exclude_count = 0
        else:
            target_count = campaign.audience.target_count
            exclude_count = campaign.audience.exclude_count
        self.store.add_history(
            HistoryRecord(
                id=None,
                executed_at=result.executed_at,
                campaign_id=campaign.id,
                subject=campaign.subject,
                mode=mode,
                target_count=target_count,
                exclude_count=exclude_count,
                drive_share_url=campaign.drive_share_url,
                success=result.ok,
                error=redact_text(result.error),
                operator_name=campaign.operator_name,
                mock=result.mock,
            )
        )
        self.store.add_audit(
            campaign.id,
            f"deliver_{mode.value}",
            campaign.operator_name,
            f"ok={result.ok} mock={result.mock} targets={target_count}",
        )
