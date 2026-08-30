"""Write dummy additions-CSV files for each format-check case."""

from __future__ import annotations

import csv
from io import StringIO
from pathlib import Path

from moriyama_mail.audience.myasp_list import EXPECTED_HEADERS

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "samples" / "宛先CSVテスト"


def _row(headers: list[str], **fields: str) -> list[str]:
    cells = [""] * len(headers)
    for name, value in fields.items():
        cells[headers.index(name)] = value
    return cells


def _ok_row(headers: list[str], *, user: str = "Ab12Cd34", email: str = "reader@example.com") -> list[str]:
    return _row(
        headers,
        **{
            "ユーザーID": user,
            "注文ID": "Or" + user,
            "メールアドレス": email,
            "配信可能/不可能": "配信可能",
            "シナリオ名（購入商品）": "サンプルメルマガ",
        },
    )


def _csv_bytes(headers: list[str], rows: list[list[str]], encoding: str, trailing_blank: int = 0) -> bytes:
    buf = StringIO()
    writer = csv.writer(buf, lineterminator="\n")
    writer.writerow(headers)
    for row in rows:
        writer.writerow(row)
    text = buf.getvalue() + ("\n" * trailing_blank)
    if encoding == "utf-8-sig":
        return text.encode("utf-8-sig")
    return text.encode(encoding)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    for old in OUT.iterdir():
        if old.is_file():
            old.unlink()

    headers = list(EXPECTED_HEADERS)
    ok = _ok_row(headers)
    cases: list[tuple[str, bytes]] = [
        ("01_通る_ShiftJIS.csv", _csv_bytes(headers, [ok], "cp932")),
        ("02_通る_UTF8.csv", _csv_bytes(headers, [ok], "utf-8")),
        ("03_通る_UTF8_BOM.csv", _csv_bytes(headers, [ok], "utf-8-sig")),
        ("04_通る_末尾空行.csv", _csv_bytes(headers, [ok], "cp932", trailing_blank=3)),
        ("05_通る_列が1本多い.csv", _csv_bytes(headers + ["余分"], [ok + [""]], "cp932")),
        ("06_止まる_メールだけの一覧.csv", "mail\na@example.com\n".encode("utf-8")),
        ("07_止まる_必須列なし.csv", "名前,メール\nA,a@example.com\n".encode("utf-8")),
        (
            "08_止まる_メール形式不正.csv",
            _csv_bytes(headers, [_ok_row(headers, email="bad-address")], "cp932"),
        ),
        (
            "09_止まる_列数不一致.csv",
            _csv_bytes(
                headers,
                [["Ab12Cd34", "Xy98Zw01", "", "", "", "reader@example.com", "", "", "配信可能", "商品"]],
                "utf-8",
            ),
        ),
        (
            "10_止まる_メール重複.csv",
            _csv_bytes(
                headers,
                [
                    _ok_row(headers, user="Ab12Cd34", email="same@example.com"),
                    _ok_row(headers, user="Xy98Zw01", email="same@example.com"),
                ],
                "utf-8",
            ),
        ),
        ("11_止まる_空ファイル.csv", b""),
        ("12_止まる_見出しだけ.csv", _csv_bytes(headers, [], "utf-8", trailing_blank=2)),
        (
            "13_止まる_配信フラグ不正.csv",
            _csv_bytes(
                headers,
                [
                    _row(
                        headers,
                        **{
                            "ユーザーID": "Ab12Cd34",
                            "注文ID": "OrAb12Cd34",
                            "メールアドレス": "reader@example.com",
                            "配信可能/不可能": "OK",
                            "シナリオ名（購入商品）": "サンプルメルマガ",
                        },
                    )
                ],
                "utf-8",
            ),
        ),
        (
            "14_止まる_ユーザーID空.csv",
            _csv_bytes(headers, [_ok_row(headers, user="")], "utf-8"),
        ),
        ("15_止まる_拡張子がtxt.txt", _csv_bytes(headers, [ok], "cp932")),
    ]

    for name, data in cases:
        (OUT / name).write_bytes(data)
        print(name, len(data))

    (OUT / "使い方.txt").write_text(
        "\n".join(
            [
                "フォームの「追加する宛先のファイル」に付けて確認するテスト用CSVです。",
                "中身はダミーです。実在の顧客アドレスは入れていません。",
                "",
                "ファイル名が「通る」で始まるもの … 受け付けてよいはずです。",
                "ファイル名が「止まる」で始まるもの … 理由を出して止めるはずです。",
                "15 は拡張子が .txt なので、中身が正しくても止まります。",
                "",
                "作り直すとき: python scripts/write_additions_test_csvs.py",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
