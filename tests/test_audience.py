from pathlib import Path

from moriyama_mail.audience.parser import AudienceParseError, AudienceParser, ColumnMapping
from moriyama_mail.domain.models import AudienceAction


def test_single_column_csv_does_not_need_official_headers(tmp_path: Path):
    path = tmp_path / "one.csv"
    path.write_text("alpha@example.com\nbravo@example.com\n", encoding="utf-8")
    parsed = AudienceParser().parse_file(path, AudienceAction.ADD)
    assert parsed.additions == ["alpha@example.com", "bravo@example.com"]


def test_named_column_is_required_when_multiple_headers_exist(tmp_path: Path):
    path = tmp_path / "multi.csv"
    path.write_text("name,address\nA,a@example.com\n", encoding="utf-8")
    try:
        AudienceParser().parse_file(path, AudienceAction.EXCLUDE)
        assert False
    except AudienceParseError as exc:
        assert "列名はまだ固定" in str(exc)


def test_mapping_can_be_supplied_later(tmp_path: Path):
    path = tmp_path / "mapped.csv"
    path.write_text("氏名,連絡先\n山田,a@example.com\n", encoding="utf-8")
    parsed = AudienceParser().parse_file(
        path,
        AudienceAction.REMOVE,
        ColumnMapping(email_column="連絡先"),
    )
    assert parsed.removals == ["a@example.com"]


def test_action_column_mapping_is_configurable(tmp_path: Path):
    path = tmp_path / "actions.csv"
    path.write_text("email,kind\na@example.com,追加\nb@example.com,除外\n", encoding="utf-8")
    parsed = AudienceParser().parse_single_file_with_actions(
        path,
        ColumnMapping(email_column="email", action_column="kind"),
    )
    assert parsed.additions == ["a@example.com"]
    assert parsed.exclusions == ["b@example.com"]
