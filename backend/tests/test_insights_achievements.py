from datetime import UTC, date, datetime, timedelta
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from sqlalchemy.dialects import postgresql

from app.bot.keyboards import when
from app.db.repositories.stats import StatsRepository
from app.services import stats
from app.services.achievements import Counters, build_achievements
from app.services.insights import compute_insights
from app.services.reminders import ReminderSetting, due_kinds, parse_settings, week_summary_text
from app.services.stats import ALL_TIME, DayStats

START = date(2026, 10, 1)


def _days(rows: list[dict[str, Any]]) -> list[DayStats]:
    return [DayStats(date=START + timedelta(days=i), **row) for i, row in enumerate(rows)]


# --- наблюдения ---


def test_insights_need_enough_days() -> None:
    days = _days([{"sleep_minutes": 480, "energy": 5}, {"sleep_minutes": 300, "energy": 2}])
    assert compute_insights(days, None) == []


def test_insight_sleep_and_energy() -> None:
    good = [{"sleep_minutes": 480, "energy": 4}] * 3
    bad = [{"sleep_minutes": 330, "energy": 2}] * 3
    text = compute_insights(_days(good + bad), None)
    assert text == ["😴 После 7+ часов сна энергия в среднем 4,0 из 5, после короткого сна — 2,0."]


def test_insight_hidden_when_difference_small() -> None:
    good = [{"sleep_minutes": 480, "mood": 4}] * 3
    bad = [{"sleep_minutes": 330, "mood": 4}] * 3
    assert compute_insights(_days(good + bad), None) == []


def test_insight_workouts_and_mood() -> None:
    rows = [{"workouts": 1, "mood": 5}] * 3 + [{"mood": 3}] * 3
    assert compute_insights(_days(rows), None) == [
        "🏋️ В дни с тренировкой настроение 5,0 из 5, без неё — 3,0."
    ]


def test_insight_kcal_and_weight() -> None:
    rows: list[dict[str, Any]] = [{"kcal": 1800.0} for _ in range(10)]
    rows[0]["weight_kg"] = 80.0
    rows[9]["weight_kg"] = 79.2
    text = compute_insights(_days(rows), 2100)
    assert text == ["⚖️ В среднем 1800 ккал в день при норме 2100 — вес за это время −0,8 кг."]


def test_insight_weight_needs_a_week() -> None:
    rows: list[dict[str, Any]] = [{"kcal": 1800.0} for _ in range(5)]
    rows[0]["weight_kg"] = 80.0
    rows[4]["weight_kg"] = 79.0
    assert compute_insights(_days(rows), None) == []


# --- достижения ---


def test_achievements_progress_capped() -> None:
    result = build_achievements(Counters(active_days=12, best_streak=5, workouts=0, checkins=7))
    by_key = {a.key: a for a in result}
    assert by_key["first_day"].achieved
    assert (by_key["streak_7"].progress, by_key["streak_7"].goal) == (5, 7)
    assert not by_key["streak_7"].achieved
    assert by_key["checkins_7"].achieved
    assert by_key["checkins_7"].progress == 7
    assert not by_key["workouts_1"].achieved


def test_records_query_compiles() -> None:
    session = AsyncMock()
    session.execute.return_value = MagicMock()
    import asyncio

    asyncio.run(StatsRepository(session).exercise_records(1, 10))
    sql = str(session.execute.await_args.args[0].compile(dialect=postgresql.dialect()))
    assert "row_number() OVER (PARTITION BY workout_sets.exercise_id" in sql
    assert "exercises.kind" in sql


# --- «всё время» ---


async def test_all_time_starts_from_first_record(monkeypatch: pytest.MonkeyPatch) -> None:
    today = date(2026, 11, 5)
    active = {date(2026, 3, 1), date(2026, 6, 1)}
    monkeypatch.setattr(StatsRepository, "active_dates", AsyncMock(return_value=active))
    user = MagicMock(id=1)
    assert await stats.period_start(AsyncMock(), user, ALL_TIME, today) == date(2026, 3, 1)


async def test_all_time_without_records(monkeypatch: pytest.MonkeyPatch) -> None:
    today = date(2026, 11, 5)
    monkeypatch.setattr(StatsRepository, "active_dates", AsyncMock(return_value=set()))
    start = await stats.period_start(AsyncMock(), MagicMock(id=1), ALL_TIME, today)
    assert start == today - timedelta(days=29)


# --- итог недели ---


def test_week_reminder_only_on_sunday() -> None:
    settings = parse_settings({"week": {"on": True}})
    moscow = ZoneInfo("Europe/Moscow")
    sunday = datetime(2026, 11, 8, 19, 5, tzinfo=moscow)
    saturday = datetime(2026, 11, 7, 19, 5, tzinfo=moscow)
    assert "week" in due_kinds(settings, sunday)
    assert "week" not in due_kinds(settings, saturday)
    assert sunday.astimezone(UTC).weekday() == 6


def test_week_shown_with_weekday() -> None:
    assert (
        when("week", ReminderSetting(on=True, time=datetime(2026, 1, 1, 19).time())) == "вс 19:00"
    )
    assert (
        when("lunch", ReminderSetting(on=True, time=datetime(2026, 1, 1, 13, 30).time())) == "13:30"
    )


def test_week_summary_text() -> None:
    rows: list[dict[str, Any]] = [
        {"kcal": 2000.0, "sleep_minutes": 450, "weight_kg": 80.0, "workouts": 1},
        {"kcal": 1800.0, "sleep_minutes": 420},
        {"mood": 4, "weight_kg": 79.6, "workouts": 1},
    ] + [{}] * 4
    text = week_summary_text(_days(rows), streak=3)
    assert text is not None
    assert "Дней с записями: 3 из 7" in text
    assert "В среднем 1900 ккал в день" in text
    assert "Сон в среднем 7 ч 15 мин" in text
    assert "Тренировок: 2" in text
    assert "Вес: −0,4 кг" in text
    assert "Серия: 3 дня подряд" in text


def test_week_summary_silent_when_empty() -> None:
    assert week_summary_text(_days([{}] * 7), streak=0) is None
