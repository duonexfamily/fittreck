from datetime import date

from sqlalchemy import select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BodyMetric, Checkin, Meal, MealItem, WaterLog, Workout


class StatsRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def active_dates(self, user_id: int, since: date) -> set[date]:
        """Дни с любой записью: еда, вода, вес, чек-ин или выполненная тренировка."""
        query = union(
            select(Meal.date)
            .join(MealItem, MealItem.meal_id == Meal.id)
            .where(Meal.user_id == user_id, Meal.date >= since),
            select(WaterLog.date).where(
                WaterLog.user_id == user_id, WaterLog.date >= since, WaterLog.ml > 0
            ),
            select(BodyMetric.date).where(
                BodyMetric.user_id == user_id,
                BodyMetric.date >= since,
                BodyMetric.weight_kg.is_not(None),
            ),
            select(Checkin.date).where(Checkin.user_id == user_id, Checkin.date >= since),
            select(Workout.date).where(
                Workout.user_id == user_id, Workout.date >= since, Workout.status == "done"
            ),
        )
        result = await self.session.execute(query)
        return set(result.scalars())
