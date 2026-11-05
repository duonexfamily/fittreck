from datetime import time
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.schemas.checkins import CheckinIn
from app.main import app
from app.services.checkins import sleep_minutes

client = TestClient(app)


@pytest.mark.parametrize(
    ("bed", "wake", "minutes"),
    [
        (time(23, 30), time(7, 0), 450),  # через полночь
        (time(0, 15), time(8, 0), 465),  # уснул после полуночи
        (time(14, 0), time(15, 30), 90),  # дневной сон
        (time(7, 0), time(7, 0), 0),
    ],
)
def test_sleep_minutes(bed: time, wake: time, minutes: int) -> None:
    assert sleep_minutes(bed, wake) == minutes


def test_sleep_minutes_needs_both_times() -> None:
    assert sleep_minutes(None, time(7, 0)) is None
    assert sleep_minutes(time(23, 0), None) is None


def test_checkin_in_accepts_partial() -> None:
    assert CheckinIn(energy=3).energy == 3
    full = CheckinIn.model_validate(
        {"bed_time": "23:30", "wake_time": "07:00", "sleep_quality": 4, "note": "ок"}
    )
    assert full.bed_time == time(23, 30)


@pytest.mark.parametrize(
    "body",
    [
        {},
        {"note": None},
        {"bed_time": "23:30"},
        {"wake_time": "07:00"},
        {"energy": 0},
        {"stress": 6},
        {"note": "x" * 1001},
    ],
)
def test_checkin_in_rejects(body: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        CheckinIn.model_validate(body)


@pytest.mark.parametrize(
    ("method", "path"),
    [("get", "/api/v1/checkins"), ("put", "/api/v1/checkins/2026-11-05")],
)
def test_checkin_endpoints_require_auth(method: str, path: str) -> None:
    assert client.request(method, path).status_code == 401
