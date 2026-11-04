from datetime import date, timedelta

import pytest
from fastapi.testclient import TestClient

from app.bot.keyboards import checkin_done_text
from app.main import app
from app.services.streaks import compute_streak, days_word

client = TestClient(app)

TODAY = date(2026, 11, 5)


def _days(*offsets: int) -> set[date]:
    """Дни относительно TODAY: 0 — сегодня, 1 — вчера."""
    return {TODAY - timedelta(days=o) for o in offsets}


def test_streak_empty() -> None:
    s = compute_streak(set(), TODAY)
    assert (s.current, s.best, s.today_done) == (0, 0, False)
    assert s.week == (False,) * 7


def test_streak_includes_today() -> None:
    s = compute_streak(_days(0, 1, 2), TODAY)
    assert (s.current, s.best, s.today_done) == (3, 3, True)


def test_streak_not_broken_until_day_ends() -> None:
    # Сегодня ещё ничего не записано — серия по вчера сохраняется
    s = compute_streak(_days(1, 2), TODAY)
    assert (s.current, s.today_done) == (2, False)


def test_streak_broken_by_missed_day() -> None:
    assert compute_streak(_days(2, 3, 4), TODAY).current == 0


def test_best_streak_from_history() -> None:
    s = compute_streak(_days(0, 10, 11, 12, 13, 20), TODAY)
    assert (s.current, s.best) == (1, 4)


def test_future_days_ignored() -> None:
    # Запланированное на завтра не должно удлинять серию
    s = compute_streak({TODAY + timedelta(days=1)} | _days(0), TODAY)
    assert (s.current, s.best) == (1, 1)


def test_week_oldest_first() -> None:
    s = compute_streak(_days(0, 6), TODAY)
    assert s.week == (True, False, False, False, False, False, True)


@pytest.mark.parametrize(
    ("n", "word"),
    [(1, "день"), (2, "дня"), (4, "дня"), (5, "дней"), (11, "дней"), (12, "дней"),
     (21, "день"), (22, "дня"), (111, "дней")],
)  # fmt: skip
def test_days_word(n: int, word: str) -> None:
    assert days_word(n) == word


def test_done_text_streak_only_from_two_days() -> None:
    values = {"sleep_quality": 4, "energy": 4, "mood": 4}
    assert "Серия" not in checkin_done_text(values, 1)
    assert "Серия: 5 дней подряд" in checkin_done_text(values, 5)


def test_streaks_endpoint_requires_auth() -> None:
    assert client.get("/api/v1/stats/streaks").status_code == 401
