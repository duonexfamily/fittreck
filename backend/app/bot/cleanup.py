"""Автоочистка чата с ботом.

Бот отправил новое сообщение — прошлое удаляем. Команды пользователя удаляем сразу
после обработки. В итоге в чате остаётся одно актуальное сообщение с кнопками.
Работает только в личных чатах. Telegram даёт удалять сообщения не старше 48 часов —
более старые просто остаются, это не ошибка.
"""

import logging
from collections.abc import Awaitable, Callable
from typing import Any

from aiogram import BaseMiddleware, Bot
from aiogram.client.session.middlewares.base import (
    BaseRequestMiddleware,
    NextRequestMiddlewareType,
)
from aiogram.enums import ChatType
from aiogram.exceptions import TelegramAPIError
from aiogram.methods import Response, SendMessage, TelegramMethod
from aiogram.methods.base import TelegramType
from aiogram.types import Message, TelegramObject
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.background import spawn
from app.services.chat_cleanup import replace_bot_message

logger = logging.getLogger(__name__)


async def safe_delete(bot: Bot, chat_id: int, message_id: int) -> None:
    """Удаляет сообщение, если получится: оно могло устареть или уже быть удалено."""
    try:
        await bot.delete_message(chat_id=chat_id, message_id=message_id)
    except TelegramAPIError:
        logger.debug("Не удалось удалить сообщение", exc_info=True)


class BotMessageCleanupMiddleware(BaseRequestMiddleware):
    """Перехватывает отправку сообщений ботом и удаляет предыдущее сообщение в чате.

    Стоит на уровне запросов к Bot API, поэтому ловит и ответы на команды,
    и напоминания планировщика.
    """

    def __init__(self, sessionmaker: async_sessionmaker[AsyncSession]) -> None:
        self.sessionmaker = sessionmaker

    async def __call__(
        self,
        make_request: NextRequestMiddlewareType[TelegramType],
        bot: Bot,
        method: TelegramMethod[TelegramType],
    ) -> Response[TelegramType]:
        response = await make_request(bot, method)
        # Вопреки аннотации aiogram цепочка возвращает сам результат метода
        # (Message, bool и т.д.), а не обёртку Response
        sent: Any = response
        # В личном чате id чата совпадает с telegram_id пользователя
        if (
            isinstance(method, SendMessage)
            and isinstance(sent, Message)
            and sent.chat.type == ChatType.PRIVATE
        ):
            # Очистка — в фоне: ответ уже доставлен, следующий шаг хендлера ждать не должен
            spawn(self._replace(bot, sent.chat.id, sent.message_id))
        return response

    async def _replace(self, bot: Bot, chat_id: int, message_id: int) -> None:
        try:
            async with self.sessionmaker() as session:
                previous = await replace_bot_message(session, chat_id, message_id)
        except Exception:
            # Очистка — не главное: сообщение уже доставлено, ошибку только логируем
            logger.warning("Не удалось запомнить сообщение бота", exc_info=True)
            return
        if previous is not None:
            await safe_delete(bot, chat_id, previous)


class DeleteIncomingMiddleware(BaseMiddleware):
    """Удаляет сообщение пользователя (команду) после того, как бот на него ответил."""

    async def __call__(
        self,
        handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
        event: TelegramObject,
        data: dict[str, Any],
    ) -> Any:
        result = await handler(event, data)
        if isinstance(event, Message) and event.chat.type == ChatType.PRIVATE and event.bot:
            spawn(safe_delete(event.bot, event.chat.id, event.message_id))
        return result
