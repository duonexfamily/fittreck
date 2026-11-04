from datetime import UTC, date, datetime, time
from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo

import pytest
from aiogram.types import Message

from app.bot.keyboards import ReminderCallback
from app.bot.routers import settings as settings_router
from app.services import reminders
from app.services.reminders import ReminderSetting, due_kinds, parse_settings, shift_time

MSK = ZoneInfo("Europe/Moscow")


def test_parse_settings_defaults() -> None:
    settings = parse_settings({})
    assert set(settings) == set(reminders.REMINDERS_BY_KIND)
    assert settings["lunch"] == ReminderSetting(on=True, time=time(13, 30))
    assert settings["weight"].on is False


def test_parse_settings_ignores_broken_values() -> None:
    settings = parse_settings(
        {"lunch": {"on": "yes", "time": "25:99"}, "dinner": "oops", "water": {"time": "17:05"}}
    )
    assert settings["lunch"] == ReminderSetting(on=True, time=time(13, 30))
    assert settings["dinner"].time == time(19, 30)
    assert settings["water"] == ReminderSetting(on=True, time=time(17, 5))


def test_dump_parse_roundtrip() -> None:
    settings = parse_settings({"weight": {"on": True, "time": "07:15"}})
    assert parse_settings(reminders.dump_settings(settings)) == settings


@pytest.mark.parametrize(
    ("at", "minutes", "expected"),
    [
        (time(13, 30), 15, time(13, 45)),
        (time(23, 30), 60, time(0, 30)),
        (time(0, 0), -15, time(23, 45)),
    ],
)
def test_shift_time_wraps(at: time, minutes: int, expected: time) -> None:
    assert shift_time(at, minutes) == expected


@pytest.mark.parametrize(
    ("local", "expected"),
    [
        (time(13, 29), []),  # ещё рано
        (time(13, 30), ["lunch"]),
        (time(14, 29), ["lunch"]),  # опоздали, но в пределах окна — досылаем
        (time(14, 30), []),  # окно прошло
    ],
)
def test_due_kinds_window(local: time, expected: list[str]) -> None:
    settings = {"lunch": ReminderSetting(on=True, time=time(13, 30))}
    now = datetime.combine(date(2026, 11, 5), local, tzinfo=MSK)
    assert list(due_kinds(settings, now)) == expected


def test_due_kinds_skips_disabled() -> None:
    settings = {"lunch": ReminderSetting(on=False, time=time(13, 30))}
    now = datetime(2026, 11, 5, 13, 30, tzinfo=MSK)
    assert list(due_kinds(settings, now)) == []


class FakeRepo:
    def __init__(self, recipients: list[tuple[Any, dict[str, Any]]], handled: set[Any]) -> None:
        self.recipients = recipients
        self.handled = handled
        self.marked: list[tuple[int, str, date]] = []

    async def handled_since(self, since: date) -> set[Any]:
        return self.handled

    async def list_recipients(self) -> list[tuple[Any, dict[str, Any]]]:
        return self.recipients

    async def mark_handled(self, user_id: int, type_: str, day: date) -> bool:
        self.marked.append((user_id, type_, day))
        return True


async def test_collect_due_uses_user_timezone(monkeypatch: pytest.MonkeyPatch) -> None:
    # 10:30 UTC = 13:30 в Москве: обед пора, а в Лондоне ещё 10:30
    moscow = SimpleNamespace(id=1, telegram_id=101, timezone="Europe/Moscow")
    london = SimpleNamespace(id=2, telegram_id=102, timezone="Europe/London")
    # Тренировка в 10:00 по Лондону тоже попала бы в окно — здесь проверяем только обед
    no_workout = {"workout": {"on": False}}
    repo = FakeRepo([(moscow, no_workout), (london, no_workout)], handled=set())
    monkeypatch.setattr(reminders, "ReminderRepository", lambda _session: repo)
    monkeypatch.setattr(reminders, "_already_done", AsyncMock(return_value=False))

    due = await reminders.collect_due(AsyncMock(), datetime(2026, 11, 5, 10, 30, tzinfo=UTC))

    assert [(item.chat_id, item.type.kind) for item in due] == [(101, "lunch")]
    assert repo.marked == [(1, "lunch", date(2026, 11, 5))]


async def test_collect_due_skips_handled_and_done(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=1, telegram_id=101, timezone="Europe/Moscow")
    now = datetime(2026, 11, 5, 10, 30, tzinfo=UTC)
    monkeypatch.setattr(reminders, "_already_done", AsyncMock(return_value=True))

    # Обед уже записан — не отправляем, но отмечаем, чтобы не проверять каждую минуту
    repo = FakeRepo([(user, {})], handled=set())
    monkeypatch.setattr(reminders, "ReminderRepository", lambda _session: repo)
    assert await reminders.collect_due(AsyncMock(), now) == []
    assert repo.marked == [(1, "lunch", date(2026, 11, 5))]

    # Уже обработано — даже не проверяем
    repo = FakeRepo([(user, {})], handled={(1, "lunch", date(2026, 11, 5))})
    monkeypatch.setattr(reminders, "ReminderRepository", lambda _session: repo)
    assert await reminders.collect_due(AsyncMock(), now) == []
    assert repo.marked == []


def _callback(data: ReminderCallback) -> SimpleNamespace:
    # Методы Message синхронные и возвращают объект запроса, поэтому edit_text подменяем отдельно
    message = MagicMock(spec=Message)
    message.edit_text = AsyncMock()
    return SimpleNamespace(
        from_user=SimpleNamespace(id=1), message=message, answer=AsyncMock(), data=data
    )


async def test_settings_requires_profile(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings_router, "get_by_telegram_id", AsyncMock(return_value=None))
    answer = AsyncMock()
    monkeypatch.setattr(settings_router, "answer_with_app", answer)
    message = SimpleNamespace(from_user=SimpleNamespace(id=1))

    await settings_router.cmd_settings(message, session=AsyncMock())  # type: ignore[arg-type]

    assert answer.await_args.args[1] == settings_router.NEED_PROFILE


@pytest.mark.parametrize(
    "data",
    [
        ReminderCallback(action="toggle", kind="hack"),
        ReminderCallback(action="shift", kind="lunch", minutes=600),
        ReminderCallback(action="delete", kind="lunch"),
    ],
)
async def test_reminder_button_rejects_bad_data(
    monkeypatch: pytest.MonkeyPatch, data: ReminderCallback
) -> None:
    user = SimpleNamespace(id=1, onboarded_at=datetime.now(UTC), timezone="Europe/Moscow")
    monkeypatch.setattr(settings_router, "get_by_telegram_id", AsyncMock(return_value=user))
    toggle, shift = AsyncMock(), AsyncMock()
    monkeypatch.setattr(reminders, "toggle", toggle)
    monkeypatch.setattr(reminders, "shift", shift)
    callback = _callback(data)

    await settings_router.on_reminder_button(callback, data, session=AsyncMock())  # type: ignore[arg-type]

    toggle.assert_not_awaited()
    shift.assert_not_awaited()
    callback.message.edit_text.assert_not_awaited()
    callback.answer.assert_awaited_once()


async def test_reminder_button_toggles(monkeypatch: pytest.MonkeyPatch) -> None:
    user = SimpleNamespace(id=1, onboarded_at=datetime.now(UTC), timezone="Europe/Moscow")
    monkeypatch.setattr(settings_router, "get_by_telegram_id", AsyncMock(return_value=user))
    toggle = AsyncMock(return_value=parse_settings({"lunch": {"on": False}}))
    monkeypatch.setattr(reminders, "toggle", toggle)
    data = ReminderCallback(action="toggle", kind="lunch")
    callback = _callback(data)

    await settings_router.on_reminder_button(callback, data, session=AsyncMock())  # type: ignore[arg-type]

    toggle.assert_awaited_once()
    assert "выключено" in callback.message.edit_text.await_args.args[0]
