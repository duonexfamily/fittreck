import time
from urllib.parse import parse_qsl, urlencode

import pytest

from app.core.security import InitDataError, validate_init_data
from tests.conftest import TEST_BOT_TOKEN, make_init_data

MAX_AGE = 24 * 60 * 60


def test_valid_init_data_returns_user(init_data: str) -> None:
    user = validate_init_data(init_data, TEST_BOT_TOKEN, MAX_AGE)
    assert user.id == 42
    assert user.first_name == "Тест"
    assert user.username == "tester"


def test_wrong_bot_token_rejected(init_data: str) -> None:
    with pytest.raises(InitDataError):
        validate_init_data(init_data, "999:other-token", MAX_AGE)


def test_tampered_user_rejected(init_data: str) -> None:
    fields = dict(parse_qsl(init_data))
    fields["user"] = fields["user"].replace("42", "43")
    with pytest.raises(InitDataError):
        validate_init_data(urlencode(fields), TEST_BOT_TOKEN, MAX_AGE)


def test_missing_hash_rejected(init_data: str) -> None:
    fields = dict(parse_qsl(init_data))
    del fields["hash"]
    with pytest.raises(InitDataError):
        validate_init_data(urlencode(fields), TEST_BOT_TOKEN, MAX_AGE)


def test_expired_rejected() -> None:
    old = int(time.time()) - MAX_AGE - 10
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(auth_date=old), TEST_BOT_TOKEN, MAX_AGE)


def test_future_auth_date_rejected() -> None:
    future = int(time.time()) + 3600
    with pytest.raises(InitDataError):
        validate_init_data(make_init_data(auth_date=future), TEST_BOT_TOKEN, MAX_AGE)


def test_duplicate_fields_rejected(init_data: str) -> None:
    with pytest.raises(InitDataError):
        validate_init_data(f"{init_data}&user=%7B%22id%22%3A1%7D", TEST_BOT_TOKEN, MAX_AGE)


@pytest.mark.parametrize("garbage", ["", "abc", "hash=", "=&="])
def test_garbage_rejected(garbage: str) -> None:
    with pytest.raises(InitDataError):
        validate_init_data(garbage, TEST_BOT_TOKEN, MAX_AGE)
