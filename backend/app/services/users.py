from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import TelegramUser
from app.db.models import User
from app.db.repositories.users import UserRepository


async def register_user(session: AsyncSession, tg_user: TelegramUser) -> User:
    """Находит или создаёт пользователя по данным Telegram. Общая точка для бота и API."""
    user = await UserRepository(session).upsert(
        telegram_id=tg_user.id,
        first_name=tg_user.first_name,
        username=tg_user.username,
        language_code=tg_user.language_code,
    )
    await session.commit()
    return user


async def get_by_telegram_id(session: AsyncSession, telegram_id: int) -> User | None:
    return await UserRepository(session).get_by_telegram_id(telegram_id)
