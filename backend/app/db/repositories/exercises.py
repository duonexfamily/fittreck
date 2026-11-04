from sqlalchemy import ColumnElement, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Exercise
from app.db.repositories.foods import _escape_like


class ExerciseRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _visible_to(user_id: int) -> ColumnElement[bool]:
        """Системные упражнения и свои. Чужие не видны."""
        return or_(Exercise.owner_id.is_(None), Exercise.owner_id == user_id)

    async def search(
        self,
        user_id: int,
        query: str,
        muscle_group: str | None,
        kind: str | None,
        limit: int,
    ) -> list[Exercise]:
        """Каталог с фильтрами. Сначала совпадения с начала названия, затем свои, по алфавиту."""
        stmt = select(Exercise).where(self._visible_to(user_id))
        order: list[ColumnElement[int] | ColumnElement[str]] = []
        if query:
            stmt = stmt.where(Exercise.name.ilike(f"%{_escape_like(query)}%", escape="\\"))
            prefix = f"{_escape_like(query)}%"
            order.append(case((Exercise.name.ilike(prefix, escape="\\"), 0), else_=1))
        if muscle_group:
            stmt = stmt.where(Exercise.muscle_group == muscle_group)
        if kind:
            stmt = stmt.where(Exercise.kind == kind)
        order += [case((Exercise.owner_id == user_id, 0), else_=1), func.lower(Exercise.name)]
        result = await self.session.execute(stmt.order_by(*order).limit(limit))
        return list(result.scalars())

    async def get_visible(self, user_id: int, exercise_id: int) -> Exercise | None:
        result = await self.session.execute(
            select(Exercise).where(Exercise.id == exercise_id, self._visible_to(user_id))
        )
        return result.scalar_one_or_none()

    async def create(self, owner_id: int, name: str, muscle_group: str, kind: str) -> Exercise:
        exercise = Exercise(owner_id=owner_id, name=name, muscle_group=muscle_group, kind=kind)
        self.session.add(exercise)
        await self.session.flush()
        return exercise
