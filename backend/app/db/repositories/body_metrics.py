from datetime import date
from decimal import Decimal

from sqlalchemy import func, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BodyMetric


class BodyMetricRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def upsert_weight(self, user_id: int, day: date, weight_kg: Decimal) -> None:
        """Записывает вес за день. Повторный ввод в тот же день перезаписывает значение."""
        stmt = (
            insert(BodyMetric)
            .values(user_id=user_id, date=day, weight_kg=weight_kg)
            .on_conflict_do_update(
                index_elements=[BodyMetric.user_id, BodyMetric.date],
                set_={"weight_kg": weight_kg},
            )
        )
        await self.session.execute(stmt)

    async def latest_weight(self, user_id: int) -> Decimal | None:
        result = await self.session.execute(
            select(BodyMetric.weight_kg)
            .where(BodyMetric.user_id == user_id, BodyMetric.weight_kg.is_not(None))
            .order_by(BodyMetric.date.desc())
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def list_weights(self, user_id: int, since: date) -> list[tuple[date, Decimal]]:
        """Вес по дням начиная с даты, от старых к новым."""
        result = await self.session.execute(
            select(BodyMetric.date, BodyMetric.weight_kg)
            .where(
                BodyMetric.user_id == user_id,
                BodyMetric.date >= since,
                BodyMetric.weight_kg.is_not(None),
            )
            .order_by(BodyMetric.date)
        )
        return [(day, weight) for day, weight in result.tuples() if weight is not None]

    async def count_weights(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count())
            .select_from(BodyMetric)
            .where(BodyMetric.user_id == user_id, BodyMetric.weight_kg.is_not(None))
        )
        return result.scalar_one()

    async def clear_weight(self, user_id: int, day: date) -> bool:
        """Стирает вес за день. False — записи не было."""
        result = await self.session.execute(
            update(BodyMetric)
            .where(
                BodyMetric.user_id == user_id,
                BodyMetric.date == day,
                BodyMetric.weight_kg.is_not(None),
            )
            .values(weight_kg=None)
            .returning(BodyMetric.id)
        )
        return result.first() is not None
