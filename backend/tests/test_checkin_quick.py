from datetime import UTC, date, datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.types import Message

from app.bot.keyboards import (
    CheckinCallback,
    checkin_done_keyboard,
    checkin_done_text,
    checkin_step_keyboard,
)
from app.bot.routers import checkin_quick
from app.bot.routers import settings as settings_router
from app.scheduler.jobs import reminder_keyboard
from app.services import checkins, reminders, streaks
from app.services.profile import user_today

URL = "https://app.example"
DAY = date(2026, 11, 5)


def _user() -> SimpleNamespace:
    return SimpleNamespace(id=1, onboarded_at=datetime.now(UTC), timezone="Europe/Moscow")


def _callback(data: CheckinCallback) -> SimpleNamespace:
    # Методы Message синхронные и возвращают объект запроса, поэтому edit_text подменяем отдельно
    message = MagicMock(spec=Message)
    message.edit_text = AsyncMock()
    return SimpleNamespace(
        from_user=SimpleNamespace(id=1), message=message, answer=AsyncMock(), data=data
    )


def test_step_keyboard_has_five_ratings_and_app_button() -> None:
    keyboard = checkin_step_keyboard("energy", DAY, URL)
    ratings, app_row = keyboard.inline_keyboard
    data = [CheckinCallback.unpack(b.callback_data or "") for b in ratings]
    assert [d.value for d in data] == [1, 2, 3, 4, 5]
    assert {(d.day, d.field) for d in data} == {("2026-11-05", "energy")}
    assert app_row[0].web_app is not None
    assert app_row[0].web_app.url == f"{URL}/checkin?date=2026-11-05"


def test_keyboards_without_https_have_no_app_button() -> None:
    assert len(checkin_step_keyboard("mood", DAY, None).inline_keyboard) == 1
    assert checkin_done_keyboard(DAY, None) is None


def test_done_keyboard_offers_sleep_time_only_when_missing() -> None:
    def label(has_sleep_time: bool) -> str:
        keyboard = checkin_done_keyboard(DAY, URL, has_sleep_time)
        assert keyboard is not None
        return keyboard.inline_keyboard[0][0].text

    assert "время сна" in label(False)
    assert "время сна" not in label(True)


def test_callback_data_fits_telegram_limit() -> None:
    # Telegram принимает callback_data не длиннее 64 байт
    for field in checkins.QUICK_FIELDS:
        packed = CheckinCallback(day="2026-11-05", field=field, value=5).pack()
        assert len(packed.encode()) <= 64


def test_next_field_order() -> None:
    assert checkin_quick.next_field("sleep_quality") == "energy"
    assert checkin_quick.next_field("energy") == "mood"
    assert checkin_quick.next_field("mood") is None


def test_done_text_skips_missing() -> None:
    text = checkin_done_text({"sleep_quality": 4, "energy": None, "mood": 5})
    assert "Сон 4/5 · настроение 5/5" in text
    assert "энергия" not in text


def test_checkin_reminder_asks_in_chat() -> None:
    item = reminders.Outgoing(1, 101, reminders.REMINDERS_BY_KIND["checkin"], DAY)
    first = reminder_keyboard(item, URL).inline_keyboard[0][0]
    assert CheckinCallback.unpack(first.callback_data or "").field == "sleep_quality"
    # Остальные напоминания по-прежнему открывают Mini App
    lunch = reminders.Outgoing(1, 101, reminders.REMINDERS_BY_KIND["lunch"], DAY)
    assert reminder_keyboard(lunch, URL).inline_keyboard[0][0].web_app is not None


@pytest.mark.parametrize(
    ("field", "value"),
    [("note", 3), ("stress", 3), ("energy", 0), ("energy", 6)],
)
async def test_save_quick_rejects_bad_values(field: str, value: int) -> None:
    session = AsyncMock()
    with pytest.raises(ValueError):
        await checkins.save_quick(session, _user(), DAY, field, value)  # type: ignore[arg-type]
    session.commit.assert_not_awaited()


async def test_save_quick_rejects_future() -> None:
    user = _user()
    tomorrow = user_today(user) + timedelta(days=1)  # type: ignore[arg-type]
    with pytest.raises(checkins.FutureDateError):
        await checkins.save_quick(AsyncMock(), user, tomorrow, "energy", 3)  # type: ignore[arg-type]


async def test_save_quick_writes_only_one_field(monkeypatch: pytest.MonkeyPatch) -> None:
    upsert = AsyncMock()
    monkeypatch.setattr(checkins.CheckinRepository, "upsert", upsert)
    session = AsyncMock()
    user = _user()
    today = user_today(user)  # type: ignore[arg-type]

    await checkins.save_quick(session, user, today, "mood", 4)  # type: ignore[arg-type]

    # Остальные поля, внесённые в приложении, не затираются
    assert upsert.await_args.args == (1, today, {"mood": 4})
    session.commit.assert_awaited_once()


@pytest.mark.parametrize(
    "data",
    [
        CheckinCallback(day="not-a-date", field="energy", value=3),
        CheckinCallback(day="2026-11-05", field="note", value=3),
        CheckinCallback(day="2026-11-05", field="energy", value=9),
        CheckinCallback(day="2999-01-01", field="energy", value=3),
    ],
)
async def test_button_rejects_bad_data(
    monkeypatch: pytest.MonkeyPatch, data: CheckinCallback
) -> None:
    monkeypatch.setattr(settings_router, "get_by_telegram_id", AsyncMock(return_value=_user()))
    upsert = AsyncMock()
    monkeypatch.setattr(checkins.CheckinRepository, "upsert", upsert)
    callback = _callback(data)

    await checkin_quick.on_checkin_button(callback, data, session=AsyncMock())  # type: ignore[arg-type]

    upsert.assert_not_awaited()
    callback.message.edit_text.assert_not_awaited()
    callback.answer.assert_awaited_once()


async def test_button_moves_to_next_question(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_router, "get_by_telegram_id", AsyncMock(return_value=_user()))
    save = AsyncMock()
    monkeypatch.setattr(checkins, "save_quick", save)
    data = CheckinCallback(day="2026-11-05", field="sleep_quality", value=4)
    callback = _callback(data)

    await checkin_quick.on_checkin_button(callback, data, session=AsyncMock())  # type: ignore[arg-type]

    assert save.await_args.args[2:] == (DAY, "sleep_quality", 4)
    assert "энергии" in callback.message.edit_text.await_args.args[0]


async def test_button_last_question_shows_summary(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_router, "get_by_telegram_id", AsyncMock(return_value=_user()))
    saved = SimpleNamespace(sleep_quality=3, energy=4, mood=5, bed_time=None)
    monkeypatch.setattr(checkins, "save_quick", AsyncMock(return_value=saved))
    streak = streaks.Streak(current=3, best=3, today_done=True, week=(True,) * 7)
    monkeypatch.setattr(streaks, "get_streak", AsyncMock(return_value=streak))
    data = CheckinCallback(day="2026-11-05", field="mood", value=5)
    callback = _callback(data)

    await checkin_quick.on_checkin_button(callback, data, session=AsyncMock())  # type: ignore[arg-type]

    text = callback.message.edit_text.await_args.args[0]
    assert "Сон 3/5 · энергия 4/5 · настроение 5/5" in text
    assert "Серия: 3 дня" in text


async def test_checkin_command_requires_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_router, "get_by_telegram_id", AsyncMock(return_value=None))
    answer = AsyncMock()
    monkeypatch.setattr(checkin_quick, "answer_with_app", answer)
    message = SimpleNamespace(from_user=SimpleNamespace(id=1))

    await checkin_quick.cmd_checkin(message, session=AsyncMock())  # type: ignore[arg-type]

    assert answer.await_args.args[1] == settings_router.NEED_PROFILE
