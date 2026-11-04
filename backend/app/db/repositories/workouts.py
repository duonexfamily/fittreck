from datetime import date

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Workout, WorkoutSet

# Подходы и их упражнения — сразу: в async ленивая загрузка не работает
_WITH_SETS = selectinload(Workout.sets).selectinload(WorkoutSet.exercise)


class WorkoutRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_range(self, user_id: int, date_from: date, date_to: date) -> list[Workout]:
        result = await self.session.execute(
            select(Workout)
            .where(Workout.user_id == user_id, Workout.date.between(date_from, date_to))
            .order_by(Workout.date.desc(), Workout.id.desc())
            .options(_WITH_SETS)
        )
        return list(result.scalars())

    async def get(self, user_id: int, workout_id: int) -> Workout | None:
        result = await self.session.execute(
            select(Workout)
            .where(Workout.id == workout_id, Workout.user_id == user_id)
            .options(_WITH_SETS)
            # После изменений подходов список должен перечитаться из БД
            .execution_options(populate_existing=True)
        )
        return result.scalar_one_or_none()

    async def add(self, workout: Workout) -> Workout:
        self.session.add(workout)
        await self.session.flush()
        return workout

    async def delete(self, workout: Workout) -> None:
        await self.session.delete(workout)

    async def get_set(self, user_id: int, set_id: int) -> WorkoutSet | None:
        """Подход — только если тренировка принадлежит пользователю."""
        result = await self.session.execute(
            select(WorkoutSet)
            .join(Workout, Workout.id == WorkoutSet.workout_id)
            .where(WorkoutSet.id == set_id, Workout.user_id == user_id)
            .options(selectinload(WorkoutSet.exercise))
        )
        return result.scalar_one_or_none()

    async def exercise_sets(self, workout_id: int, exercise_id: int) -> list[WorkoutSet]:
        """Подходы одного упражнения в тренировке по порядку."""
        result = await self.session.execute(
            select(WorkoutSet)
            .where(WorkoutSet.workout_id == workout_id, WorkoutSet.exercise_id == exercise_id)
            .order_by(WorkoutSet.set_no, WorkoutSet.id)
        )
        return list(result.scalars())

    async def add_set(self, item: WorkoutSet) -> WorkoutSet:
        self.session.add(item)
        await self.session.flush()
        return item

    async def delete_set(self, item: WorkoutSet) -> None:
        await self.session.delete(item)
        await self.session.flush()
