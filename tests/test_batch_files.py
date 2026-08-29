from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_batch_files_are_ascii_without_bom():
    bats = sorted(ROOT.glob("*.bat")) + sorted((ROOT / "scripts").glob("*.bat"))
    assert bats, "batch files should exist"
    for path in bats:
        data = path.read_bytes()
        assert not data.startswith(b"\xef\xbb\xbf"), f"{path.name} has a UTF-8 BOM"
        assert not data.startswith(b"\xff\xfe"), f"{path.name} is UTF-16"
        data.decode("ascii")
        assert b"\r\n" in data, f"{path.name} must use CRLF"
        assert b"\n" not in data.replace(b"\r\n", b""), f"{path.name} has lone LF"
