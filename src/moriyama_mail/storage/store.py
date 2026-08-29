from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timezone
from pathlib import Path

from moriyama_mail.domain.models import (
    AudienceChangeSet,
    Campaign,
    CampaignStatus,
    DeliveryMode,
    HistoryRecord,
    utc_now,
)
from moriyama_mail.domain.status import apply_derived_status

SCHEMA = """
CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL,
    subject TEXT NOT NULL DEFAULT '',
    body TEXT NOT NULL DEFAULT '',
    notes TEXT NOT NULL DEFAULT '',
    material_path TEXT NOT NULL DEFAULT '',
    material_name TEXT NOT NULL DEFAULT '',
    drive_file_id TEXT NOT NULL DEFAULT '',
    drive_share_url TEXT NOT NULL DEFAULT '',
    test_recipients TEXT NOT NULL DEFAULT '[]',
    delivery_mode TEXT NOT NULL DEFAULT 'test',
    status TEXT NOT NULL DEFAULT '依頼受付',
    error_message TEXT NOT NULL DEFAULT '',
    operator_name TEXT NOT NULL DEFAULT '',
    production_locked INTEGER NOT NULL DEFAULT 0,
    test_result TEXT NOT NULL DEFAULT '',
    production_result TEXT NOT NULL DEFAULT '',
    test_sent_at TEXT,
    production_sent_at TEXT,
    scheduled_at TEXT,
    source_channel TEXT NOT NULL DEFAULT 'dedicated_form',
    myasp_plan_key TEXT NOT NULL DEFAULT '',
    myasp_plan_name TEXT NOT NULL DEFAULT '',
    send_timing TEXT NOT NULL DEFAULT 'scheduled'
);

CREATE TABLE IF NOT EXISTS audience_entries (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    campaign_id TEXT NOT NULL,
    action TEXT NOT NULL,
    email TEXT NOT NULL,
    FOREIGN KEY(campaign_id) REFERENCES campaigns(id)
);

CREATE TABLE IF NOT EXISTS delivery_history (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    executed_at TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    subject TEXT NOT NULL,
    mode TEXT NOT NULL,
    target_count INTEGER NOT NULL,
    exclude_count INTEGER NOT NULL,
    drive_share_url TEXT NOT NULL DEFAULT '',
    success INTEGER NOT NULL,
    error TEXT NOT NULL DEFAULT '',
    operator_name TEXT NOT NULL DEFAULT '',
    mock INTEGER NOT NULL DEFAULT 1
);

CREATE TABLE IF NOT EXISTS audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    created_at TEXT NOT NULL,
    campaign_id TEXT NOT NULL,
    action TEXT NOT NULL,
    operator_name TEXT NOT NULL DEFAULT '',
    detail TEXT NOT NULL DEFAULT ''
);
"""


def _dt(value: datetime | None) -> str | None:
    if value is None:
        return None
    return value.astimezone(timezone.utc).isoformat()


def _parse_dt(value: str | None) -> datetime | None:
    if not value:
        return None
    return datetime.fromisoformat(value)


class Store:
    def __init__(self, path: Path) -> None:
        self.path = path
        path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(path)
        self._conn.row_factory = sqlite3.Row
        self._conn.execute("PRAGMA foreign_keys = ON")
        self._conn.executescript(SCHEMA)
        self._migrate()
        self._conn.commit()

    def _migrate(self) -> None:
        cols = {row[1] for row in self._conn.execute("PRAGMA table_info(campaigns)")}
        additions = {
            "myasp_plan_key": "TEXT NOT NULL DEFAULT ''",
            "myasp_plan_name": "TEXT NOT NULL DEFAULT ''",
            "send_timing": "TEXT NOT NULL DEFAULT 'scheduled'",
        }
        for name, ddl in additions.items():
            if name not in cols:
                self._conn.execute(f"ALTER TABLE campaigns ADD COLUMN {name} {ddl}")

    def close(self) -> None:
        self._conn.close()

    def save_campaign(self, campaign: Campaign) -> Campaign:
        apply_derived_status(campaign)
        campaign.updated_at = utc_now()
        self._conn.execute(
            """
            INSERT INTO campaigns (
                id, created_at, updated_at, subject, body, notes,
                material_path, material_name, drive_file_id, drive_share_url,
                test_recipients, delivery_mode, status, error_message, operator_name,
                production_locked, test_result, production_result,
                test_sent_at, production_sent_at, scheduled_at, source_channel,
                myasp_plan_key, myasp_plan_name, send_timing
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                updated_at=excluded.updated_at,
                subject=excluded.subject,
                body=excluded.body,
                notes=excluded.notes,
                material_path=excluded.material_path,
                material_name=excluded.material_name,
                drive_file_id=excluded.drive_file_id,
                drive_share_url=excluded.drive_share_url,
                test_recipients=excluded.test_recipients,
                delivery_mode=excluded.delivery_mode,
                status=excluded.status,
                error_message=excluded.error_message,
                operator_name=excluded.operator_name,
                production_locked=excluded.production_locked,
                test_result=excluded.test_result,
                production_result=excluded.production_result,
                test_sent_at=excluded.test_sent_at,
                production_sent_at=excluded.production_sent_at,
                scheduled_at=excluded.scheduled_at,
                source_channel=excluded.source_channel,
                myasp_plan_key=excluded.myasp_plan_key,
                myasp_plan_name=excluded.myasp_plan_name,
                send_timing=excluded.send_timing
            """,
            (
                campaign.id,
                _dt(campaign.created_at),
                _dt(campaign.updated_at),
                campaign.subject,
                campaign.body,
                campaign.notes,
                campaign.material_path,
                campaign.material_name,
                campaign.drive_file_id,
                campaign.drive_share_url,
                json.dumps(list(campaign.test_recipients), ensure_ascii=False),
                campaign.delivery_mode.value,
                campaign.status.value,
                campaign.error_message,
                campaign.operator_name,
                1 if campaign.production_locked else 0,
                campaign.test_result,
                campaign.production_result,
                _dt(campaign.test_sent_at),
                _dt(campaign.production_sent_at),
                _dt(campaign.scheduled_at),
                campaign.source_channel,
                campaign.myasp_plan_key,
                campaign.myasp_plan_name,
                campaign.send_timing,
            ),
        )
        self._conn.execute("DELETE FROM audience_entries WHERE campaign_id = ?", (campaign.id,))
        rows = (
            [(campaign.id, "add", email) for email in campaign.audience.additions]
            + [(campaign.id, "remove", email) for email in campaign.audience.removals]
            + [(campaign.id, "exclude", email) for email in campaign.audience.exclusions]
        )
        if rows:
            self._conn.executemany(
                "INSERT INTO audience_entries (campaign_id, action, email) VALUES (?, ?, ?)",
                rows,
            )
        self._conn.commit()
        return campaign

    def get_campaign(self, campaign_id: str) -> Campaign | None:
        row = self._conn.execute("SELECT * FROM campaigns WHERE id = ?", (campaign_id,)).fetchone()
        if row is None:
            return None
        return self._campaign_from_row(row)

    def list_campaigns(self) -> list[Campaign]:
        rows = self._conn.execute("SELECT * FROM campaigns ORDER BY created_at DESC").fetchall()
        return [self._campaign_from_row(row) for row in rows]

    def add_history(self, record: HistoryRecord) -> HistoryRecord:
        cursor = self._conn.execute(
            """
            INSERT INTO delivery_history (
                executed_at, campaign_id, subject, mode, target_count, exclude_count,
                drive_share_url, success, error, operator_name, mock
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                _dt(record.executed_at),
                record.campaign_id,
                record.subject,
                record.mode.value,
                record.target_count,
                record.exclude_count,
                record.drive_share_url,
                1 if record.success else 0,
                record.error,
                record.operator_name,
                1 if record.mock else 0,
            ),
        )
        self._conn.commit()
        return HistoryRecord(
            id=cursor.lastrowid,
            executed_at=record.executed_at,
            campaign_id=record.campaign_id,
            subject=record.subject,
            mode=record.mode,
            target_count=record.target_count,
            exclude_count=record.exclude_count,
            drive_share_url=record.drive_share_url,
            success=record.success,
            error=record.error,
            operator_name=record.operator_name,
            mock=record.mock,
        )

    def list_history(self, campaign_id: str | None = None) -> list[HistoryRecord]:
        if campaign_id:
            rows = self._conn.execute(
                "SELECT * FROM delivery_history WHERE campaign_id = ? ORDER BY executed_at DESC",
                (campaign_id,),
            ).fetchall()
        else:
            rows = self._conn.execute(
                "SELECT * FROM delivery_history ORDER BY executed_at DESC"
            ).fetchall()
        return [self._history_from_row(row) for row in rows]

    def add_audit(self, campaign_id: str, action: str, operator_name: str, detail: str = "") -> None:
        self._conn.execute(
            "INSERT INTO audit_log (created_at, campaign_id, action, operator_name, detail) VALUES (?, ?, ?, ?, ?)",
            (_dt(utc_now()), campaign_id, action, operator_name, detail),
        )
        self._conn.commit()

    def list_audit(self, campaign_id: str | None = None) -> list[dict[str, str]]:
        if campaign_id:
            rows = self._conn.execute(
                "SELECT * FROM audit_log WHERE campaign_id = ? ORDER BY created_at DESC",
                (campaign_id,),
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM audit_log ORDER BY created_at DESC").fetchall()
        return [dict(row) for row in rows]

    def _campaign_from_row(self, row: sqlite3.Row) -> Campaign:
        recipients = tuple(json.loads(row["test_recipients"] or "[]"))
        audience_rows = self._conn.execute(
            "SELECT action, email FROM audience_entries WHERE campaign_id = ?",
            (row["id"],),
        ).fetchall()
        audience = AudienceChangeSet()
        for item in audience_rows:
            if item["action"] == "add":
                audience.additions.append(item["email"])
            elif item["action"] == "remove":
                audience.removals.append(item["email"])
            elif item["action"] == "exclude":
                audience.exclusions.append(item["email"])
        campaign = Campaign(
            id=row["id"],
            created_at=_parse_dt(row["created_at"]) or utc_now(),
            updated_at=_parse_dt(row["updated_at"]) or utc_now(),
            subject=row["subject"],
            body=row["body"],
            notes=row["notes"],
            material_path=row["material_path"],
            material_name=row["material_name"],
            drive_file_id=row["drive_file_id"],
            drive_share_url=row["drive_share_url"],
            test_recipients=recipients,
            delivery_mode=DeliveryMode(row["delivery_mode"]),
            status=CampaignStatus(row["status"]),
            error_message=row["error_message"],
            operator_name=row["operator_name"],
            production_locked=bool(row["production_locked"]),
            test_result=row["test_result"],
            production_result=row["production_result"],
            test_sent_at=_parse_dt(row["test_sent_at"]),
            production_sent_at=_parse_dt(row["production_sent_at"]),
            scheduled_at=_parse_dt(row["scheduled_at"]),
            audience=audience,
            source_channel=row["source_channel"],
            myasp_plan_key=row["myasp_plan_key"] if "myasp_plan_key" in row.keys() else "",
            myasp_plan_name=row["myasp_plan_name"] if "myasp_plan_name" in row.keys() else "",
            send_timing=row["send_timing"] if "send_timing" in row.keys() else "scheduled",
        )
        return apply_derived_status(campaign)

    def _history_from_row(self, row: sqlite3.Row) -> HistoryRecord:
        return HistoryRecord(
            id=row["id"],
            executed_at=_parse_dt(row["executed_at"]) or utc_now(),
            campaign_id=row["campaign_id"],
            subject=row["subject"],
            mode=DeliveryMode(row["mode"]),
            target_count=row["target_count"],
            exclude_count=row["exclude_count"],
            drive_share_url=row["drive_share_url"],
            success=bool(row["success"]),
            error=row["error"],
            operator_name=row["operator_name"],
            mock=bool(row["mock"]),
        )
