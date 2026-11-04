"""Рассылка напоминаний.

Раз в минуту выбираем, кому пора напомнить, и отправляем с паузой: у Telegram
лимит около 30 сообщений в секунду. Работает внутри процесса — нужна одна реплика,
но и при двух дублей не будет: отметки в reminder_log ставятся до отправки.
"""

import asyncio
import logging
from datetime import UTC, datetime

from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramForbiddenError, TelegramRetryAfter
from aiogram.types import InlineKeyboardMarkup
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.keyboards import checkin_step_keyboard, open_app_keyboard
from app.db.models import User
from app.services import checkins, reminders

logger = logging.getLogger(__name__)

# Пауза между сообщениями, секунды (~25 в секунду)
SEND_PAUSE = 0.04


def reminder_keyboard(item: reminders.Outgoing, webapp_url: str) -> InlineKeyboardMarkup:
    # На чек-ин отвечают прямо в чате: оценки кнопками, подробности — в приложении
    if item.type.kind == "checkin":
        return checkin_step_keyboard(checkins.QUICK_FIELDS[0], item.day, webapp_url)
    return open_app_keyboard(webapp_url, item.type.path, item.type.button)


async def _send(bot: Bot, item: reminders.Outgoing, webapp_url: str) -> None:
    keyboard = reminder_keyboard(item, webapp_url)
    try:
        await bot.send_message(item.chat_id, item.type.text, reply_markup=keyboard)
    except TelegramRetryAfter as error:
        # Превысили лимит — ждём, сколько просит Telegram, и пробуем ещё раз
        await asyncio.sleep(error.retry_after)
        await bot.send_message(item.chat_id, item.type.text, reply_markup=keyboard)


async def run_once(
    bot: Bot, sessionmaker: async_sessionmaker[AsyncSession], webapp_url: str, now: datetime
) -> int:
    """Один проход рассылки. Возвращает число отправленных напоминаний."""
    async with sessionmaker() as session:
        due = await reminders.collect_due(session, now)

    sent = 0
    for item in due:
        try:
            await _send(bot, item, webapp_url)
            sent += 1
        except TelegramForbiddenError:
            # Бот заблокирован — больше не пишем этому пользователю
            async with sessionmaker() as session:
                user = await session.get(User, item.user_id)
                if user is not None:
                    await reminders.disable_all(session, user)
            logger.info("Бот заблокирован пользователем, напоминания выключены")
        except TelegramAPIError:
            logger.warning("Не удалось отправить напоминание", exc_info=True)
        await asyncio.sleep(SEND_PAUSE)
    return sent


async def reminders_loop(
    bot: Bot, sessionmaker: async_sessionmaker[AsyncSession], webapp_url: str
) -> None:
    while True:
        # Просыпаемся в начале каждой минуты
        now = datetime.now(UTC)
        await asyncio.sleep(60 - now.second - now.microsecond / 1_000_000)
        # Ошибка одного прохода не должна останавливать цикл
        try:
            sent = await run_once(bot, sessionmaker, webapp_url, datetime.now(UTC))
            if sent:
                logger.info("Отправлено напоминаний: %s", sent)
        except Exception:
            logger.exception("Ошибка рассылки напоминаний")
