from pathlib import Path

from moriyama_mail.audience.myasp_list import check_myasp_userlist, is_csv_filename
from tests.additions_fixtures import fixture_path

REAL_SAMPLE_DIR = Path(
    r"d:\仕事別\ホームページ系\常連客\不動産のエデン株式会社様（盛山さん）\メルマガ配信\20260829"
)
REAL_SAMPLE_NAMES = (
    "ユーザーリスト_サンプルメルマガ_20260830113047.csv",
    "ユーザーリスト_闇菓子カフェ in 赤羽（20251210）_20260830113729.csv",
    "ユーザーリスト_盗難事件B_20260830113747.csv",
)


def test_csv_filename_only():
    assert is_csv_filename("ユーザーリスト_sample.csv")
    assert is_csv_filename(r"C:\tmp\USER.CSV")
    assert not is_csv_filename("15_止まる_拡張子がtxt.txt")
    assert not is_csv_filename("list.xlsx")


def test_extra_column_is_warning_only():
    result = check_myasp_userlist(fixture_path("05_通る_列が1本多い.csv"))
    assert result.ok
    assert any(item.code == "header_shape" and item.severity == "warning" for item in result.issues)


def test_current_myasp_downloads_pass_format_check():
    found = 0
    for name in REAL_SAMPLE_NAMES:
        path = REAL_SAMPLE_DIR / name
        if not path.is_file():
            continue
        result = check_myasp_userlist(path)
        assert result.ok, [item.message for item in result.errors]
        assert result.encoding == "cp932"
        assert result.column_count == 84
        assert result.row_count >= 1
        found += 1
    if found == 0:
        return
    assert found == len(REAL_SAMPLE_NAMES)
