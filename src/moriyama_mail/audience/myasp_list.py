"""Format check for MyASP user-list CSV exports (現行ダウンロード)."""

from __future__ import annotations

import csv
import re
from dataclasses import dataclass, field
from io import StringIO
from pathlib import Path

from moriyama_mail.audience.parser import EMAIL_RE

REQUIRED_HEADERS = (
    "ユーザーID",
    "注文ID",
    "メールアドレス",
    "配信可能/不可能",
    "シナリオ名（購入商品）",
)

EXPECTED_HEADERS = (
    "ユーザーID",
    "注文ID",
    "会社名",
    "姓",
    "名",
    "メールアドレス",
    "ユーザー共通のポイント数",
    "シナリオ別のポイント数",
    "配信可能/不可能",
    "シナリオ名（購入商品）",
    "購読状態",
    "受領状態",
    "最終ステップメールグループ",
    "最終ステップ",
    "登録日",
    "本登録完了日時",
    "有効期限",
    "フリガナ",
    "郵便番号",
    "都道府県",
    "住所",
    "電話番号",
    "イベント・ウェビナー開催日",
    "メモ",
    "フリー項目１（１行テキスト）",
    "フリー項目２（複数行テキスト）",
    "フリー項目３（ラジオボタン）",
    "フリー項目４（チェックボックス）",
    "フリー項目５（プルダウンリスト）",
    "フリー項目６（隠しデータ）",
    "フリー項目７（日付：年月日）",
    "フリー項目８（日付：月日）",
    "フリー項目９",
    "フリー項目１０",
    "フリー項目１１",
    "フリー項目１２",
    "フリー項目１３",
    "フリー項目１４",
    "フリー項目１５",
    "フリー項目１６",
    "フリー項目１７",
    "フリー項目１８",
    "フリー項目１９",
    "フリー項目２０",
    "フリー項目２１",
    "フリー項目２２",
    "フリー項目２３",
    "フリー項目２４",
    "フリー項目２５",
    "フリー項目２６",
    "フリー項目２７",
    "フリー項目２８",
    "フリー項目２９",
    "フリー項目３０",
    "フリー項目３１",
    "フリー項目３２",
    "フリー項目３３",
    "フリー項目３４",
    "フリー項目３５",
    "フリー項目３６",
    "フリー項目３７",
    "フリー項目３８",
    "フリー項目３９",
    "フリー項目４０",
    "フリー項目４１",
    "フリー項目４２",
    "フリー項目４３",
    "フリー項目４４",
    "フリー項目４５",
    "フリー項目４６",
    "フリー項目４７",
    "フリー項目４８",
    "フリー項目４９",
    "フリー項目５０",
    "登録フォームURL",
    "登録フォームの前のページのURL",
    "ラベル",
    "支払方法",
    "支払方法表示名",
    "トータル金額",
    "購入商品",
    "サブアドレス",
    "支払備考欄",
    "配信解除日",
)

ALLOW_VALUES = {"配信可能", "配信不可能"}
USER_ID_RE = re.compile(r"^[A-Za-z0-9_-]+$")
ENCODINGS = ("utf-8-sig", "utf-8", "cp932")


@dataclass(frozen=True)
class FormatIssue:
    row: int
    code: str
    message: str
    severity: str = "error"


@dataclass
class FormatCheckResult:
    ok: bool
    encoding: str = ""
    source_name: str = ""
    row_count: int = 0
    column_count: int = 0
    issues: list[FormatIssue] = field(default_factory=list)

    @property
    def errors(self) -> list[FormatIssue]:
        return [item for item in self.issues if item.severity == "error"]


def check_myasp_userlist(path: Path) -> FormatCheckResult:
    """Check a MyASP user-list CSV. Does not log or return addresses."""
    return check_myasp_userlist_bytes(Path(path).read_bytes(), Path(path).name)


def is_csv_filename(name: str) -> bool:
    return Path(name or "").name.lower().endswith(".csv")


def check_myasp_userlist_bytes(data: bytes, source_name: str = "") -> FormatCheckResult:
    issues: list[FormatIssue] = []
    if source_name and not is_csv_filename(source_name):
        return FormatCheckResult(
            ok=False,
            source_name=source_name,
            issues=[FormatIssue(0, "extension", "宛先ファイルはCSV（.csv）だけ使えます。")],
        )
    if not data:
        return FormatCheckResult(
            ok=False,
            source_name=source_name,
            issues=[FormatIssue(0, "empty", "ファイルが空です。")],
        )
    lower_name = source_name.lower()
    if data.startswith(b"PK") or lower_name.endswith(".xlsx") or lower_name.endswith(".xls"):
        return FormatCheckResult(
            ok=False,
            source_name=source_name,
            issues=[FormatIssue(0, "csv", "Excelのままでは使えません。")],
        )

    text, encoding = _decode(data)
    if text is None:
        return FormatCheckResult(
            ok=False,
            source_name=source_name,
            issues=[
                FormatIssue(
                    0,
                    "encoding",
                    "文字コードを判定できません。UTF-8 または Shift_JIS（CP932）のCSVにしてください。",
                )
            ],
        )

    if source_name and not source_name.startswith("ユーザーリスト_"):
        issues.append(
            FormatIssue(
                0,
                "filename",
                "MyASPのユーザーリストは「ユーザーリスト_」で始まる名前です。",
                "warning",
            )
        )

    try:
        rows = list(csv.reader(StringIO(text)))
    except csv.Error as exc:
        return FormatCheckResult(
            ok=False,
            encoding=encoding,
            source_name=source_name,
            issues=[FormatIssue(0, "csv", f"CSVとして読めません（{exc}）。")],
        )
    if not rows:
        return FormatCheckResult(
            ok=False,
            encoding=encoding,
            source_name=source_name,
            issues=[FormatIssue(0, "header", "見出し行がありません。")],
        )

    headers = [(cell or "").strip() for cell in rows[0]]
    if headers:
        headers[0] = headers[0].lstrip("\ufeff")
    header_count = len(headers)
    header_set = set(headers)
    missing = [name for name in REQUIRED_HEADERS if name not in header_set]
    if missing:
        issues.append(
            FormatIssue(
                1,
                "headers",
                "必須列がありません: " + "、".join(missing) + f"（見出しは{header_count}列）。",
            )
        )
    if headers != list(EXPECTED_HEADERS):
        issues.append(
            FormatIssue(
                1,
                "header_shape",
                f"列の並びが現行のMyASPユーザーリスト（{len(EXPECTED_HEADERS)}列）と違います。今の見出しは{header_count}列です。",
                "warning" if not missing else "error",
            )
        )

    data_rows = _drop_trailing_empty(rows[1:])
    if not data_rows:
        issues.append(
            FormatIssue(
                0,
                "no_rows",
                "データ行がありません。末尾の空行は除いています。",
            )
        )

    if not missing:
        index = {name: i for i, name in enumerate(headers)}
        seen_emails: dict[str, int] = {}
        for offset, raw in enumerate(data_rows, start=2):
            issues.extend(_check_row(offset, raw, index, header_count, seen_emails))

    errors = [item for item in issues if item.severity == "error"]
    return FormatCheckResult(
        ok=not errors,
        encoding=encoding,
        source_name=source_name,
        row_count=len(data_rows),
        column_count=header_count,
        issues=issues,
    )


def _decode(data: bytes) -> tuple[str | None, str]:
    found: list[tuple[str, str]] = []
    fallback: list[tuple[str, str]] = []
    for encoding in ENCODINGS:
        try:
            text = data.decode(encoding)
        except UnicodeDecodeError:
            continue
        if "メールアドレス" in text:
            found.append((text, encoding))
        else:
            fallback.append((text, encoding))
    if found:
        return found[0]
    if fallback:
        return fallback[0]
    return None, ""


def _is_empty_row(raw: list[str]) -> bool:
    return all(not (cell or "").strip() for cell in raw)


def _drop_trailing_empty(rows: list[list[str]]) -> list[list[str]]:
    trimmed = list(rows)
    while trimmed and _is_empty_row(trimmed[-1]):
        trimmed.pop()
    return trimmed


def _check_row(
    row_no: int,
    raw: list[str],
    index: dict[str, int],
    header_count: int,
    seen_emails: dict[str, int],
) -> list[FormatIssue]:
    issues: list[FormatIssue] = []
    actual = len(raw)
    if actual != header_count:
        issues.append(
            FormatIssue(
                row_no,
                "col_count",
                f"列数が見出し（{header_count}列）と違います。この行は{actual}列です。",
            )
        )

    user_id = _cell(raw, index, "ユーザーID")
    order_id = _cell(raw, index, "注文ID")
    email = _cell(raw, index, "メールアドレス")
    allow = _cell(raw, index, "配信可能/不可能")

    if not user_id:
        issues.append(FormatIssue(row_no, "user_id", "ユーザーIDが空です。"))
    elif not USER_ID_RE.match(user_id):
        issues.append(FormatIssue(row_no, "user_id", "ユーザーIDの形式が正しくありません。"))

    if not order_id:
        issues.append(FormatIssue(row_no, "order_id", "注文IDが空です。"))
    elif not USER_ID_RE.match(order_id):
        issues.append(FormatIssue(row_no, "order_id", "注文IDの形式が正しくありません。"))

    if not email:
        issues.append(FormatIssue(row_no, "email", "メールアドレスが空です。"))
    elif not EMAIL_RE.match(email):
        issues.append(FormatIssue(row_no, "email", "メールアドレスの形式が正しくありません。"))
    else:
        key = email.casefold()
        first = seen_emails.get(key)
        if first is not None:
            issues.append(
                FormatIssue(
                    row_no,
                    "duplicate",
                    f"同じメールアドレスが{first}行目にもあります。",
                )
            )
        else:
            seen_emails[key] = row_no

    if allow and allow not in ALLOW_VALUES:
        issues.append(
            FormatIssue(
                row_no,
                "allow",
                "配信可能/不可能の値が正しくありません（「配信可能」または「配信不可能」）。",
            )
        )
    elif not allow:
        issues.append(FormatIssue(row_no, "allow", "配信可能/不可能が空です。"))
    return issues


HOW_TO_ATTACH = (
    "MyASPからダウンロードしたユーザーリストを、追加や修正したCSVを付けてください。"
)


def additions_format_error(data: bytes, source_name: str = "") -> str | None:
    """Return an error message if the additions file is not a MyASP user list."""
    result = check_myasp_userlist_bytes(data, source_name)
    if result.ok:
        return None
    codes = {item.code for item in result.errors}
    details: list[str] = []
    for item in result.errors:
        if item.row:
            details.append(f"{item.row}行目: {item.message}")
        else:
            details.append(item.message)

    if codes & {"extension"}:
        intro = [
            "このファイルは使えません。",
            "宛先ファイルはCSV（.csv）だけ使えます。",
            "Excelやテキストのままでは送れません。",
        ]
    elif codes & {"empty"}:
        intro = ["このファイルは使えません。", "宛先ファイルが空です。", HOW_TO_ATTACH]
    elif codes & {"encoding", "csv"}:
        intro = [
            "このファイルは使えません。",
            "CSVとして読めません。文字コードは UTF-8 または Shift_JIS（CP932）にしてください。",
            HOW_TO_ATTACH,
        ]
    elif codes & {"headers", "header", "header_shape"}:
        intro = [
            "このファイルは使えません。",
            "MyASPのユーザーリストの形式ではありません。",
            HOW_TO_ATTACH,
            "メールアドレスだけを書いた一覧は使えません。",
        ]
    else:
        intro = [
            "このファイルは使えません。",
            "ユーザーリストの内容に誤りがあります。CSVを直してから送ってください。",
        ]

    lines = intro + ["", "理由:"] + details
    stats: list[str] = []
    if result.encoding:
        stats.append(f"文字コード: {result.encoding}")
    if result.column_count:
        stats.append(f"見出しの列数: {result.column_count}")
    stats.append(f"データ行数: {result.row_count}")
    lines.extend(["", "（" + "、".join(stats) + "）"])
    return "\n".join(lines)


def _cell(raw: list[str], index: dict[str, int], name: str) -> str:
    pos = index.get(name)
    if pos is None or pos >= len(raw):
        return ""
    return (raw[pos] or "").strip()
