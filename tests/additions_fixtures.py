"""Catalog of dummy additions CSVs under samples/宛先CSVテスト."""

from pathlib import Path

FIXTURE_DIR = Path(__file__).resolve().parents[1] / "samples" / "宛先CSVテスト"

PASS_FILES = {
    "01_通る_ShiftJIS.csv": {"encoding": "cp932", "row_count": 1, "column_count": 84},
    "02_通る_UTF8.csv": {"encoding": {"utf-8", "utf-8-sig"}, "row_count": 1, "column_count": 84},
    "03_通る_UTF8_BOM.csv": {"encoding": "utf-8-sig", "row_count": 1, "column_count": 84},
    "04_通る_末尾空行.csv": {"encoding": "cp932", "row_count": 1, "column_count": 84},
    "05_通る_列が1本多い.csv": {"encoding": "cp932", "row_count": 1, "column_count": 85},
}

FAIL_FILES = {
    "06_止まる_メールだけの一覧.csv": ["形式ではありません", "理由:", "メールアドレスだけ"],
    "07_止まる_必須列なし.csv": ["必須列がありません", "理由:"],
    "08_止まる_メール形式不正.csv": ["メールアドレスの形式", "2行目", "理由:"],
    "09_止まる_列数不一致.csv": ["列数が見出し", "84列", "10列", "2行目", "理由:"],
    "10_止まる_メール重複.csv": ["同じメールアドレス", "2行目", "3行目", "理由:"],
    "11_止まる_空ファイル.csv": ["空です"],
    "12_止まる_見出しだけ.csv": ["データ行がありません"],
    "13_止まる_配信フラグ不正.csv": ["配信可能/不可能", "2行目", "理由:"],
    "14_止まる_ユーザーID空.csv": ["ユーザーIDが空", "2行目", "理由:"],
    "15_止まる_拡張子がtxt.txt": ["CSV（.csv）だけ"],
}

PRIVATE = ("example.com", "reader@", "same@", "a@example", "bad-address")


def fixture_path(name: str) -> Path:
    path = FIXTURE_DIR / name
    assert path.is_file(), f"missing {path}"
    return path
