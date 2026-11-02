from datetime import date

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db.models import Meal, MealItem


class MealRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    async def list_for_day(self, user_id: int, day: date) -> list[Meal]:
        result = await self.session.execute(
            select(Meal)
            .where(Meal.user_id == user_id, Meal.date == day)
            .options(selectinload(Meal.items))
        )
        return list(result.scalars())

    async def get_or_create(self, user_id: int, day: date, meal_type: str) -> Meal:
        """Приём пищи за день. Создаётся при первом добавлении продукта."""
        await self.session.execute(
            insert(Meal)
            .values(user_id=user_id, date=day, meal_type=meal_type)
            .on_conflict_do_nothing(index_elements=[Meal.user_id, Meal.date, Meal.meal_type])
        )
        result = await self.session.execute(
            select(Meal).where(
                Meal.user_id == user_id, Meal.date == day, Meal.meal_type == meal_type
            )
        )
        return result.scalar_one()

    async def get_item(self, user_id: int, item_id: int) -> MealItem | None:
        """Продукт из дневника — только если приём пищи принадлежит пользователю."""
        result = await self.session.execute(
            select(MealItem)
            .join(Meal, Meal.id == MealItem.meal_id)
            .where(MealItem.id == item_id, Meal.user_id == user_id)
        )
        return result.scalar_one_or_none()

    async def add_item(self, item: MealItem) -> MealItem:
        self.session.add(item)
        await self.session.flush()
        return item

    async def delete_item(self, item: MealItem) -> None:
        await self.session.delete(item)
