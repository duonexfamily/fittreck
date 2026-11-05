from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramBadRequest
from aiogram.methods import EditMessageText, SendMessage

from app.bot import cleanup
from app.services import chat_cleanup


def _sessionmaker() -> MagicMock:
    # async with sessionmaker() as session — отдаём мок-сессию
    maker = MagicMock()
    maker.return_value.__aenter__ = AsyncMock(return_value=AsyncMock())
    maker.return_value.__aexit__ = AsyncMock(return_value=False)
    return maker


def _sent(chat_type: str = ChatType.PRIVATE, message_id: int = 20) -> MagicMock:
    from aiogram.types import Message

    message = MagicMock(spec=Message)
    message.chat = SimpleNamespace(id=1, type=chat_type)
    message.message_id = message_id
    return message


async def _run(method: object, result: object, previous: int | None) -> AsyncMock:
    bot = AsyncMock()
    replace = AsyncMock(return_value=previous)
    with pytest.MonkeyPatch.context() as mp:
        mp.setattr(cleanup, "replace_bot_message", replace)
        middleware = cleanup.BotMessageCleanupMiddleware(_sessionmaker())
        make_request = AsyncMock(return_value=SimpleNamespace(result=result))
        await middleware(make_request, bot, method)  # type: ignore[arg-type]
    return bot


async def test_new_message_deletes_previous() -> None:
    bot = await _run(SendMessage(chat_id=1, text="hi"), _sent(), previous=10)
    bot.delete_message.assert_awaited_once_with(chat_id=1, message_id=10)


async def test_first_message_deletes_nothing() -> None:
    bot = await _run(SendMessage(chat_id=1, text="hi"), _sent(), previous=None)
    bot.delete_message.assert_not_awaited()


async def test_group_chat_untouched() -> None:
    bot = await _run(SendMessage(chat_id=-5, text="hi"), _sent(ChatType.GROUP), previous=10)
    bot.delete_message.assert_not_awaited()


async def test_edit_is_not_tracked() -> None:
    method = EditMessageText(chat_id=1, message_id=3, text="hi")
    bot = await _run(method, _sent(), previous=10)
    bot.delete_message.assert_not_awaited()


async def test_safe_delete_ignores_old_messages() -> None:
    # Сообщения старше 48 часов Telegram удалить не даёт — это не должно ронять бота
    bot = AsyncMock()
    bot.delete_message.side_effect = TelegramBadRequest(
        method=MagicMock(), message="message can't be deleted"
    )
    await cleanup.safe_delete(bot, 1, 2)


async def test_incoming_command_deleted_after_answer() -> None:
    from aiogram.types import Message

    message = MagicMock(spec=Message)
    message.chat = SimpleNamespace(id=1, type=ChatType.PRIVATE)
    message.message_id = 7
    message.bot = AsyncMock()
    handler = AsyncMock(return_value="ok")

    result = await cleanup.DeleteIncomingMiddleware()(handler, message, {})

    assert result == "ok"
    message.bot.delete_message.assert_awaited_once_with(chat_id=1, message_id=7)


async def test_service_skips_same_message(monkeypatch: pytest.MonkeyPatch) -> None:
    repo = MagicMock()
    repo.return_value.swap_last_bot_message = AsyncMock(return_value=5)
    monkeypatch.setattr(chat_cleanup, "UserRepository", repo)
    assert await chat_cleanup.replace_bot_message(AsyncMock(), 1, 5) is None
    assert await chat_cleanup.replace_bot_message(AsyncMock(), 1, 6) == 5
