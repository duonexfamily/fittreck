from datetime import date
from unittest.mock import AsyncMock

import pytest

from app.scheduler.jobs import reminder_keyboard
from app.services import reminders
from app.services.reminders import REMINDERS_BY_KIND, DayFacts, Outgoing, day_summary_text

DAY = date(2026, 11, 5)
URL = "https://app.example"


def _facts(**kw: object) -> DayFacts:
    base: dict[str, object] = {
        "kcal": None,
        "kcal_target": None,
        "water_ml": 0,
        "water_target_ml": 2000,
        "workouts": 0,
        "checkin": False,
        "streak": 0,
    }
    return DayFacts(**{**base, **kw})  # type: ignore[arg-type]


def test_summary_lists_what_was_logged() -> None:
    text = day_summary_text(
        _facts(kcal=1834.6, kcal_target=2100, water_ml=1500, workouts=1, checkin=True, streak=5)
    )
    assert text is not None
    assert "🍽 1835 из 2100 ккал" in text
    assert "💧 1,5 из 2,0 л" in text
    assert "Тренировка выполнена" in text
    assert "Чек-ин есть" in text
    assert "Серия: 5 дней подряд" in text


def test_summary_without_target_and_short_streak() -> None:
    text = day_summary_text(_facts(kcal=900, streak=1))
    assert text is not None
    assert "🍽 900 ккал" in text
    # Серию из одного дня не хвалим
    assert "Серия" not in text


def test_summary_warns_when_streak_at_risk() -> None:
    text = day_summary_text(_facts(streak=3))
    assert text is not None
    assert "серия 3 дня может прерваться" in text


def test_summary_silent_when_nothing_to_say() -> None:
    assert day_summary_text(_facts()) is None


def test_new_reminders_defaults() -> None:
    # Тренировка напоминает только о запланированном — можно включить сразу
    assert REMINDERS_BY_KIND["workout"].default_on is True
    # Вечерний итог — новое сообщение, включается по желанию
    assert REMINDERS_BY_KIND["summary"].default_on is False


async def test_workout_reminder_opens_planned_workout(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reminders, "_planned_workout_id", AsyncMock(return_value=42))
    composed = await reminders._compose(AsyncMock(), None, "workout", DAY)  # type: ignore[arg-type]
    assert composed == (None, "/workouts/42")


async def test_workout_reminder_skipped_without_plan(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reminders, "_planned_workout_id", AsyncMock(return_value=None))
    assert await reminders._compose(AsyncMock(), None, "workout", DAY) is None  # type: ignore[arg-type]


async def test_summary_reminder_skipped_when_empty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(reminders, "_day_facts", AsyncMock(return_value=_facts()))
    assert await reminders._compose(AsyncMock(), None, "summary", DAY) is None  # type: ignore[arg-type]


async def test_other_reminders_use_static_text() -> None:
    assert await reminders._compose(AsyncMock(), None, "lunch", DAY) == (None, None)  # type: ignore[arg-type]


def test_keyboard_uses_personal_path() -> None:
    item = Outgoing(1, 101, REMINDERS_BY_KIND["workout"], DAY, None, "/workouts/42")
    button = reminder_keyboard(item, URL).inline_keyboard[0][0]
    assert button.web_app is not None
    assert button.web_app.url == f"{URL}/workouts/42"
