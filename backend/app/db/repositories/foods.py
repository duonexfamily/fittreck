from decimal import Decimal

from sqlalchemy import ColumnElement, case, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Food, Meal, MealItem


def _escape_like(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")


class FoodRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.session = session

    @staticmethod
    def _visible_to(user_id: int) -> ColumnElement[bool]:
        """Системные продукты и свои. Чужие не видны."""
        return or_(Food.owner_id.is_(None), Food.owner_id == user_id)

    async def search(self, user_id: int, query: str, limit: int) -> list[Food]:
        """Поиск по подстроке. Сначала совпадения с начала названия, затем свои, затем короткие."""
        pattern = f"%{_escape_like(query)}%"
        prefix = f"{_escape_like(query)}%"
        result = await self.session.execute(
            select(Food)
            .where(self._visible_to(user_id), Food.name.ilike(pattern, escape="\\"))
            .order_by(
                case((Food.name.ilike(prefix, escape="\\"), 0), else_=1),
                case((Food.owner_id == user_id, 0), else_=1),
                func.length(Food.name),
                Food.name,
            )
            .limit(limit)
        )
        return list(result.scalars())

    async def recent(self, user_id: int, limit: int) -> list[Food]:
        """Недавно добавленные пользователем продукты — для пустого поиска."""
        last_used = (
            select(MealItem.food_id, func.max(MealItem.id).label("last_id"))
            .join(Meal, Meal.id == MealItem.meal_id)
            .where(Meal.user_id == user_id, MealItem.food_id.is_not(None))
            .group_by(MealItem.food_id)
            .subquery()
        )
        result = await self.session.execute(
            select(Food)
            .join(last_used, last_used.c.food_id == Food.id)
            .where(self._visible_to(user_id))
            .order_by(last_used.c.last_id.desc())
            .limit(limit)
        )
        return list(result.scalars())

    async def get_visible(self, user_id: int, food_id: int) -> Food | None:
        result = await self.session.execute(
            select(Food).where(Food.id == food_id, self._visible_to(user_id))
        )
        return result.scalar_one_or_none()

    async def create(
        self,
        owner_id: int,
        name: str,
        kcal: Decimal,
        protein: Decimal,
        fat: Decimal,
        carbs: Decimal,
    ) -> Food:
        food = Food(owner_id=owner_id, name=name, kcal=kcal, protein=protein, fat=fat, carbs=carbs)
        self.session.add(food)
        await self.session.flush()
        return food
