from datetime import date
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Checkin


class CheckinRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_range(self, user_id: int, date_from: date, date_to: date) -> list[Checkin]:
        """Чек-ины за период, от старых к новым."""
        result = await self.session.execute(
            select(Checkin)
            .where(Checkin.user_id == user_id, Checkin.date.between(date_from, date_to))
            .order_by(Checkin.date)
        )
        return list(result.scalars())

    async def exists(self, user_id: int, day: date) -> bool:
        result = await self.session.execute(
            select(Checkin.id).where(Checkin.user_id == user_id, Checkin.date == day)
        )
        return result.first() is not None

    async def upsert(self, user_id: int, day: date, values: dict[str, Any]) -> Checkin:
        """Записывает чек-ин за день. Повторная запись заменяет все поля."""
        stmt = (
            insert(Checkin)
            .values(user_id=user_id, date=day, **values)
            .on_conflict_do_update(index_elements=[Checkin.user_id, Checkin.date], set_=values)
            .returning(Checkin)
            # Объект мог остаться в сессии от прошлого чтения — берём свежие значения
            .execution_options(populate_existing=True)
        )
        result = await self.session.execute(stmt)
        return result.scalar_one()
