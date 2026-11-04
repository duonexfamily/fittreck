from datetime import date

from sqlalchemy import func, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import BodyMetric, Checkin, Meal, MealItem, WaterLog, Workout, WorkoutSet


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

    async def daily_weight(self, user_id: int, date_from: date, date_to: date) -> dict[date, float]:
        result = await self.session.execute(
            select(BodyMetric.date, BodyMetric.weight_kg).where(
                BodyMetric.user_id == user_id,
                BodyMetric.date.between(date_from, date_to),
                BodyMetric.weight_kg.is_not(None),
            )
        )
        return {day: float(kg) for day, kg in result.all() if kg is not None}

    async def daily_kcal(self, user_id: int, date_from: date, date_to: date) -> dict[date, float]:
        """Сумма калорий по дням. Дни без продуктов в ответ не попадают."""
        result = await self.session.execute(
            select(Meal.date, func.sum(MealItem.kcal))
            .join(MealItem, MealItem.meal_id == Meal.id)
            .where(Meal.user_id == user_id, Meal.date.between(date_from, date_to))
            .group_by(Meal.date)
        )
        return {day: float(kcal) for day, kcal in result.all()}

    async def daily_workouts(
        self, user_id: int, date_from: date, date_to: date
    ) -> dict[date, tuple[int, float]]:
        """Выполненные тренировки по дням: (число тренировок, объём кг).

        Объём — повторы × вес по выполненным подходам. Подходы без веса дают 0.
        """
        volume = (
            select(
                WorkoutSet.workout_id,
                func.coalesce(func.sum(WorkoutSet.reps * WorkoutSet.weight_kg), 0).label("kg"),
            )
            .where(WorkoutSet.done.is_(True))
            .group_by(WorkoutSet.workout_id)
            .subquery()
        )
        result = await self.session.execute(
            select(
                Workout.date,
                func.count(Workout.id),
                func.coalesce(func.sum(volume.c.kg), 0),
            )
            .outerjoin(volume, volume.c.workout_id == Workout.id)
            .where(
                Workout.user_id == user_id,
                Workout.date.between(date_from, date_to),
                Workout.status == "done",
            )
            .group_by(Workout.date)
        )
        return {day: (int(count), float(kg)) for day, count, kg in result.all()}
