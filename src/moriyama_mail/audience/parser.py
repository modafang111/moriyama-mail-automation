from __future__ import annotations

import csv
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path

from moriyama_mail.domain.models import AudienceAction, AudienceChangeSet

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", re.I)


class AudienceParseError(ValueError):
    pass


@dataclass(frozen=True)
class ColumnMapping:
    """User-supplied mapping. No official CSV column names are assumed."""

    email_column: str | None = None
    action_column: str | None = None
    action_values: Mapping[str, AudienceAction] | None = None
    encoding: str = "utf-8-sig"


class AudienceParser:
    """CSV parsing only. Does not talk to MyASP."""

    def parse_file(
        self,
        path: Path,
        action: AudienceAction,
        mapping: ColumnMapping | None = None,
    ) -> AudienceChangeSet:
        mapping = mapping or ColumnMapping()
        rows, headers = self._read_rows(path, mapping.encoding)
        emails = self._extract_emails(rows, headers, mapping)
        return self._to_changeset(emails, action, path.name)

    def parse_single_file_with_actions(
        self,
        path: Path,
        mapping: ColumnMapping,
    ) -> AudienceChangeSet:
        if not mapping.email_column or not mapping.action_column:
            raise AudienceParseError("1ファイルで読み込む場合はメール列と区分列の指定が必要です。")
        rows, headers = self._read_rows(path, mapping.encoding)
        if mapping.email_column not in headers or mapping.action_column not in headers:
            raise AudienceParseError("指定した列名がCSVにありません。")
        values = mapping.action_values or {
            "add": AudienceAction.ADD,
            "追加": AudienceAction.ADD,
            "remove": AudienceAction.REMOVE,
            "削除": AudienceAction.REMOVE,
            "exclude": AudienceAction.EXCLUDE,
            "除外": AudienceAction.EXCLUDE,
        }
        grouped: dict[AudienceAction, list[str]] = {
            AudienceAction.ADD: [],
            AudienceAction.REMOVE: [],
            AudienceAction.EXCLUDE: [],
        }
        skipped = 0
        seen: dict[AudienceAction, set[str]] = {k: set() for k in grouped}
        for row in rows:
            email = (row.get(mapping.email_column) or "").strip().lower()
            raw_action = (row.get(mapping.action_column) or "").strip()
            action = values.get(raw_action) or values.get(raw_action.lower())
            if not email or not EMAIL_RE.match(email) or action is None:
                skipped += 1
                continue
            if email not in seen[action]:
                seen[action].add(email)
                grouped[action].append(email)
        return AudienceChangeSet(
            additions=grouped[AudienceAction.ADD],
            removals=grouped[AudienceAction.REMOVE],
            exclusions=grouped[AudienceAction.EXCLUDE],
            skipped=skipped,
            source_name=path.name,
        )

    def _read_rows(self, path: Path, encoding: str) -> tuple[list[dict[str, str]], list[str]]:
        try:
            text = path.read_text(encoding=encoding)
        except UnicodeDecodeError:
            text = path.read_text(encoding="cp932")
        lines = text.splitlines()
        if not lines:
            return [], []
        sample = text[:4096]
        try:
            dialect = csv.Sniffer().sniff(sample, delimiters=",\t;")
        except csv.Error:
            dialect = csv.excel
        raw_rows = list(csv.reader(lines, dialect=dialect))
        if not raw_rows:
            return [], []
        first = [(cell or "").strip() for cell in raw_rows[0]]
        headerless = bool(first) and all(
            not cell or EMAIL_RE.match(cell.lower()) for cell in first
        ) and any(first)
        if headerless:
            headers = [f"column_{i + 1}" for i in range(len(first))]
            data = raw_rows
        else:
            headers = first
            data = raw_rows[1:]
        rows = []
        for raw in data:
            row = {headers[i]: (raw[i].strip() if i < len(raw) else "") for i in range(len(headers))}
            rows.append(row)
        return rows, headers

    def _extract_emails(
        self,
        rows: Sequence[Mapping[str, str]],
        headers: Sequence[str],
        mapping: ColumnMapping,
    ) -> tuple[list[str], int]:
        column = mapping.email_column
        if column and column not in headers:
            raise AudienceParseError("指定したメール列がCSVにありません。")
        if not column:
            if len(headers) == 1:
                column = headers[0]
            elif headers:
                raise AudienceParseError(
                    "CSVの列名はまだ固定していません。画面でメールアドレス列を指定してください。"
                )
            else:
                column = None
        emails: list[str] = []
        seen: set[str] = set()
        skipped = 0
        if column is None:
            # header-less single column
            for row in rows:
                values = [v for v in row.values() if v]
                raw = values[0] if values else ""
                email = raw.strip().lower()
                if not email or not EMAIL_RE.match(email):
                    skipped += 1
                    continue
                if email not in seen:
                    seen.add(email)
                    emails.append(email)
            return emails, skipped

        for row in rows:
            email = (row.get(column) or "").strip().lower()
            if not email or not EMAIL_RE.match(email):
                skipped += 1
                continue
            if email not in seen:
                seen.add(email)
                emails.append(email)
        return emails, skipped

    def _to_changeset(
        self,
        parsed: tuple[list[str], int],
        action: AudienceAction,
        source_name: str,
    ) -> AudienceChangeSet:
        emails, skipped = parsed
        change = AudienceChangeSet(skipped=skipped, source_name=source_name)
        if action is AudienceAction.ADD:
            change.additions = emails
        elif action is AudienceAction.REMOVE:
            change.removals = emails
        else:
            change.exclusions = emails
        return change


def merge_changes(*sets: AudienceChangeSet) -> AudienceChangeSet:
    merged = AudienceChangeSet()
    names: list[str] = []
    for item in sets:
        merged.additions = _unique(merged.additions + item.additions)
        merged.removals = _unique(merged.removals + item.removals)
        merged.exclusions = _unique(merged.exclusions + item.exclusions)
        merged.skipped += item.skipped
        if item.source_name:
            names.append(item.source_name)
    merged.source_name = ", ".join(names)
    return merged


def _unique(values: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for value in values:
        key = value.lower()
        if key not in seen:
            seen.add(key)
            out.append(value)
    return out
