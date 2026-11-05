"""Чистый чат: у пользователя в чате с ботом остаётся только последнее сообщение бота."""

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.repositories.users import UserRepository


async def replace_bot_message(
    session: AsyncSession, telegram_id: int, message_id: int
) -> int | None:
    """Запоминает новое сообщение бота. Возвращает id прошлого, которое нужно удалить.

    Для незарегистрированного пользователя ничего не хранится — вернётся None.
    """
    previous = await UserRepository(session).swap_last_bot_message(telegram_id, message_id)
    await session.commit()
    return previous if previous != message_id else None
