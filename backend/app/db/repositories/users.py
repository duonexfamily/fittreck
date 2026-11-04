from sqlalchemy import delete, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User


class UserRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self, telegram_id: int) -> User | None:
        result = await self.session.execute(select(User).where(User.telegram_id == telegram_id))
        return result.scalar_one_or_none()

    async def upsert(
        self,
        telegram_id: int,
        first_name: str,
        username: str | None,
        language_code: str | None,
    ) -> User:
        """Создаёт пользователя или обновляет имя и username."""
        stmt = (
            insert(User)
            .values(
                telegram_id=telegram_id,
                first_name=first_name,
                username=username,
                language_code=language_code,
            )
            .on_conflict_do_update(
                index_elements=[User.telegram_id],
                set_={"first_name": first_name, "username": username},
            )
            .returning(User)
        )
        # populate_existing: обновить объект, если он уже загружен в эту сессию
        result = await self.session.execute(stmt, execution_options={"populate_existing": True})
        return result.scalar_one()

    async def delete(self, user_id: int) -> None:
        """Удаляет пользователя. Все его записи удаляет БД каскадом (ON DELETE CASCADE)."""
        await self.session.execute(delete(User).where(User.id == user_id))
