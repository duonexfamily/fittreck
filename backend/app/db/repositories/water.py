from datetime import date

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import WaterLog


class WaterRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def get_ml(self, user_id: int, day: date) -> int:
        result = await self.session.execute(
            select(WaterLog.ml).where(WaterLog.user_id == user_id, WaterLog.date == day)
        )
        return result.scalar_one_or_none() or 0

    async def add_ml(self, user_id: int, day: date, delta_ml: int) -> int:
        """Прибавляет к сумме за день (отрицательное — отмена). Ниже нуля не опускается."""
        insert_stmt = insert(WaterLog).values(user_id=user_id, date=day, ml=max(0, delta_ml))
        stmt = insert_stmt.on_conflict_do_update(
            index_elements=[WaterLog.user_id, WaterLog.date],
            set_={"ml": func.greatest(0, WaterLog.ml + delta_ml), "updated_at": func.now()},
        ).returning(WaterLog.ml)
        result = await self.session.execute(stmt)
        ml: int = result.scalar_one()
        return ml
