from datetime import date

from sqlalchemy import func, select, union
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import (
    BodyMetric,
    Checkin,
    Exercise,
    Meal,
    MealItem,
    WaterLog,
    Workout,
    WorkoutSet,
)


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

    async def exercise_records(
        self, user_id: int, limit: int
    ) -> list[tuple[str, float, int, date]]:
        """Лучший подход по весу в каждом силовом упражнении: (название, кг, повторы, дата).

        Считаются только выполненные подходы выполненных тренировок. Новые рекорды — первыми.
        """
        ranked = (
            select(
                Exercise.name,
                WorkoutSet.weight_kg,
                WorkoutSet.reps,
                Workout.date,
                func.row_number()
                .over(
                    partition_by=WorkoutSet.exercise_id,
                    # При равном весе лучше больше повторов, при равных — первый раз
                    order_by=(
                        WorkoutSet.weight_kg.desc(),
                        WorkoutSet.reps.desc().nulls_last(),
                        Workout.date,
                    ),
                )
                .label("rank"),
            )
            .join(Workout, Workout.id == WorkoutSet.workout_id)
            .join(Exercise, Exercise.id == WorkoutSet.exercise_id)
            .where(
                Workout.user_id == user_id,
                Workout.status == "done",
                WorkoutSet.done.is_(True),
                WorkoutSet.weight_kg > 0,
                Exercise.kind == "strength",
            )
            .subquery()
        )
        result = await self.session.execute(
            select(ranked.c.name, ranked.c.weight_kg, ranked.c.reps, ranked.c.date)
            .where(ranked.c.rank == 1)
            .order_by(ranked.c.date.desc(), ranked.c.weight_kg.desc())
            .limit(limit)
        )
        return [(name, float(kg), reps or 0, day) for name, kg, reps, day in result.all()]

    async def count_done_workouts(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(Workout.id)).where(
                Workout.user_id == user_id, Workout.status == "done"
            )
        )
        return int(result.scalar_one())

    async def count_checkins(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count(Checkin.id)).where(Checkin.user_id == user_id)
        )
        return int(result.scalar_one())
