from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import TemplateSet, WorkoutTemplate

# Подходы и их упражнения — сразу: в async ленивая загрузка не работает
_WITH_SETS = selectinload(WorkoutTemplate.sets).selectinload(TemplateSet.exercise)


class TemplateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_all(self, user_id: int) -> list[WorkoutTemplate]:
        """Шаблоны пользователя по алфавиту."""
        result = await self.session.execute(
            select(WorkoutTemplate)
            .where(WorkoutTemplate.user_id == user_id)
            .order_by(func.lower(WorkoutTemplate.name), WorkoutTemplate.id)
            .options(_WITH_SETS)
        )
        return list(result.scalars())

    async def count(self, user_id: int) -> int:
        result = await self.session.execute(
            select(func.count()).where(WorkoutTemplate.user_id == user_id)
        )
        return result.scalar_one()

    async def get(self, user_id: int, template_id: int) -> WorkoutTemplate | None:
        result = await self.session.execute(
            select(WorkoutTemplate)
            .where(WorkoutTemplate.id == template_id, WorkoutTemplate.user_id == user_id)
            .options(_WITH_SETS)
        )
        return result.scalar_one_or_none()

    async def add(self, template: WorkoutTemplate) -> WorkoutTemplate:
        self.session.add(template)
        await self.session.flush()
        return template

    async def delete(self, template: WorkoutTemplate) -> None:
        await self.session.delete(template)
