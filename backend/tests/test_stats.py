from collections.abc import Iterator
from datetime import date, time
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from app.api.deps import get_current_user, get_session
from app.api.v1 import stats as stats_router
from app.main import app
from app.services import stats
from app.services.stats import build_summary

client = TestClient(app)

D1, D2, D3 = date(2026, 11, 3), date(2026, 11, 4), date(2026, 11, 5)


def test_summary_has_every_day_with_gaps() -> None:
    checkin = SimpleNamespace(
        date=D2,
        bed_time=time(23, 0),
        wake_time=time(7, 0),
        sleep_quality=4,
        energy=3,
        stress=2,
        mood=5,
    )
    days = build_summary(
        D1,
        D3,
        weight={D1: 72.4},
        kcal={D2: 1834.6},
        checkins=[checkin],  # type: ignore[list-item]
        workouts={D3: (1, 2450.0)},
    )

    assert [d.date for d in days] == [D1, D2, D3]
    # Нет данных — None, чтобы график рисовал разрыв, а не падение до нуля
    assert (days[0].weight_kg, days[1].weight_kg) == (72.4, None)
    assert (days[0].kcal, days[1].kcal) == (None, 1835)
    assert (days[1].sleep_minutes, days[1].energy, days[1].mood) == (480, 3, 5)
    assert days[0].sleep_minutes is None
    assert (days[2].workouts, days[2].volume_kg) == (1, 2450.0)
    assert (days[0].workouts, days[0].volume_kg) == (0, 0)


def test_summary_single_day() -> None:
    days = build_summary(D3, D3, weight={}, kcal={}, checkins=[], workouts={})
    assert len(days) == 1


async def test_summary_rejects_unknown_period() -> None:
    with pytest.raises(ValueError):
        await stats.get_summary(None, None, 14)  # type: ignore[arg-type]


def test_summary_endpoint_requires_auth() -> None:
    assert client.get("/api/v1/stats/summary?days=30").status_code == 401


@pytest.fixture
def authed(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    """Запрос от пользователя без БД: проверка initData и сессия подменены."""
    app.dependency_overrides[get_current_user] = lambda: SimpleNamespace(
        id=1, timezone="Europe/Moscow"
    )
    app.dependency_overrides[get_session] = lambda: None
    yield
    app.dependency_overrides.clear()


@pytest.mark.parametrize("days", [7, 30, 90])
def test_summary_endpoint_accepts_periods(
    authed: None, monkeypatch: pytest.MonkeyPatch, days: int
) -> None:
    # Из query период приходит строкой — раньше это давало 422 и пустой экран «Прогресс»
    fake = AsyncMock(return_value=build_summary(D3, D3, {}, {}, [], {}))
    monkeypatch.setattr(stats_router, "get_summary", fake)

    response = client.get(f"/api/v1/stats/summary?days={days}")

    assert response.status_code == 200
    assert fake.await_args.args[2] == days


@pytest.mark.parametrize("query", ["?days=14", "?days=abc"])
def test_summary_endpoint_rejects_bad_period(authed: None, query: str) -> None:
    assert client.get(f"/api/v1/stats/summary{query}").status_code == 422
