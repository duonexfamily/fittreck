from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from app.bot.routers import fallback, start
from app.bot.setup import on_error


def _message(first_name: str = "Аня") -> SimpleNamespace:
    user = SimpleNamespace(
        id=1, first_name=first_name, last_name=None, username=None, language_code="ru"
    )
    return SimpleNamespace(from_user=user, answer=AsyncMock())


async def test_start_escapes_name(monkeypatch: pytest.MonkeyPatch) -> None:
    # Имя с HTML-символами не должно ломать разметку сообщения
    monkeypatch.setattr(start, "register_user", AsyncMock())
    message = _message("<b>Tom & Jerry</b>")

    await start.cmd_start(message, session=AsyncMock())  # type: ignore[arg-type]

    text = message.answer.await_args.args[0]
    assert "&lt;b&gt;Tom &amp; Jerry&lt;/b&gt;" in text
    # Своя разметка в приветствии есть, но имя пользователя в неё не попадает сырым
    assert "<b>Tom" not in text
    # Приветствие перечисляет команды
    assert "/checkin" in text and "/settings" in text


async def test_help_answers() -> None:
    message = _message()
    await start.cmd_help(message)  # type: ignore[arg-type]
    assert "/start" in message.answer.await_args.args[0]


async def test_fallback_answers() -> None:
    message = _message()
    await fallback.any_message(message)  # type: ignore[arg-type]
    message.answer.assert_awaited_once()


async def test_error_handler_swallows() -> None:
    # True — ошибка обработана, webhook ответит 200, и Telegram не будет повторять апдейт
    event = SimpleNamespace(exception=RuntimeError("boom"))
    assert await on_error(event) is True  # type: ignore[arg-type]
