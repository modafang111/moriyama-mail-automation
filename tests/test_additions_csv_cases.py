from io import BytesIO

import pytest

from moriyama_mail.audience.myasp_list import additions_format_error, check_myasp_userlist
from moriyama_mail.intake.webapp import create_app
from moriyama_mail.notify import mailer
from tests.additions_fixtures import FAIL_FILES, FIXTURE_DIR, PASS_FILES, PRIVATE, fixture_path


def _pdf():
    return (BytesIO(b"%PDF-1.4 mock"), "shiryo.pdf")


def test_fixture_folder_matches_catalog():
    names = {
        path.name
        for path in FIXTURE_DIR.iterdir()
        if path.name[:1].isdigit() and path.suffix in {".csv", ".txt"}
    }
    assert names == set(PASS_FILES) | set(FAIL_FILES)
    empty = fixture_path("11_止まる_空ファイル.csv")
    assert empty.stat().st_size == 0


@pytest.mark.parametrize("name", list(PASS_FILES), ids=list(PASS_FILES))
def test_pass_csv_is_accepted(name):
    expect = PASS_FILES[name]
    path = fixture_path(name)
    result = check_myasp_userlist(path)
    assert result.ok, [item.message for item in result.errors]
    encoding = expect["encoding"]
    if isinstance(encoding, set):
        assert result.encoding in encoding
    else:
        assert result.encoding == encoding
    assert result.row_count == expect["row_count"]
    assert result.column_count == expect["column_count"]
    assert additions_format_error(path.read_bytes(), name) is None


@pytest.mark.parametrize("name", list(FAIL_FILES), ids=list(FAIL_FILES))
def test_fail_csv_explains_without_addresses(name):
    path = fixture_path(name)
    error = additions_format_error(path.read_bytes(), name)
    assert error
    for needle in FAIL_FILES[name]:
        assert needle in error
    for secret in PRIVATE:
        assert secret not in error


@pytest.mark.parametrize("name", list(PASS_FILES), ids=list(PASS_FILES))
def test_form_accepts_pass_csv(service, name):
    path = fixture_path(name)
    response = create_app(service).test_client().post(
        "/request",
        data={
            "myasp_plan_key": "test_plan",
            "subject": f"通る {name}",
            "body": "本文を送ります",
            "material": _pdf(),
            "additions_csv": (BytesIO(path.read_bytes()), name),
        },
    )
    assert response.status_code == 200, response.get_data(as_text=True)
    assert "依頼を受け付けました" in response.get_data(as_text=True)
    assert service.list_campaigns()


@pytest.mark.parametrize("name", list(FAIL_FILES), ids=list(FAIL_FILES))
def test_form_rejects_fail_csv(service, name):
    path = fixture_path(name)
    response = create_app(service).test_client().post(
        "/request",
        data={
            "myasp_plan_key": "test_plan",
            "subject": f"止まる {name}",
            "body": "本文を送ります",
            "material": _pdf(),
            "additions_csv": (BytesIO(path.read_bytes()), name),
        },
    )
    text = response.get_data(as_text=True)
    assert response.status_code == 400, text
    for needle in FAIL_FILES[name]:
        assert needle in text
    for secret in PRIVATE:
        assert secret not in text
    assert service.list_campaigns() == []


@pytest.mark.parametrize("name", list(PASS_FILES), ids=list(PASS_FILES))
def test_notify_sends_pass_csv(monkeypatch, name):
    called: list[bool] = []

    class FakeNotify:
        @staticmethod
        def notify_note(*args, **kwargs):
            called.append(True)
            return True

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(mailer, "_shared_notify", lambda: FakeNotify)
    path = fixture_path(name)
    assert (
        mailer.notify_request_received(
            request_id="ok",
            subject="件名",
            attachments=[(f"atesaki_{name}", path.read_bytes())],
        )
        is True
    )
    assert called == [True]


@pytest.mark.parametrize("name", list(FAIL_FILES), ids=list(FAIL_FILES))
def test_notify_blocks_fail_csv(monkeypatch, name):
    called: list[bool] = []

    class FakeNotify:
        @staticmethod
        def notify_note(*args, **kwargs):
            called.append(True)
            return True

    monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
    monkeypatch.setattr(mailer, "_shared_notify", lambda: FakeNotify)
    path = fixture_path(name)
    assert (
        mailer.notify_request_received(
            request_id="ng",
            subject="件名",
            attachments=[(f"atesaki_{name}", path.read_bytes())],
        )
        is False
    )
    assert called == []
