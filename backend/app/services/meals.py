"""Дневник питания: справочник продуктов, приёмы пищи, итоги дня."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from typing import Literal, Protocol, get_args

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Food, MealItem, User
from app.db.repositories.foods import FoodRepository
from app.db.repositories.meals import MealRepository
from app.services.profile import user_today

MealType = Literal["breakfast", "lunch", "dinner", "snack"]
MEAL_TYPES: tuple[MealType, ...] = get_args(MealType)

SEARCH_LIMIT = 30
RECENT_LIMIT = 20
FAVORITES_LIMIT = 50

_CENT = Decimal("0.01")


class HasNutrients(Protocol):
    """Продукт справочника, запись дневника или итог — всё, у чего есть КБЖУ."""

    @property
    def kcal(self) -> Decimal: ...
    @property
    def protein(self) -> Decimal: ...
    @property
    def fat(self) -> Decimal: ...
    @property
    def carbs(self) -> Decimal: ...


@dataclass(frozen=True, slots=True)
class Nutrients:
    kcal: Decimal
    protein: Decimal
    fat: Decimal
    carbs: Decimal


ZERO = Nutrients(Decimal(0), Decimal(0), Decimal(0), Decimal(0))


def _round(value: Decimal) -> Decimal:
    return value.quantize(_CENT, rounding=ROUND_HALF_UP)


def scale(source: HasNutrients, factor: Decimal) -> Nutrients:
    """КБЖУ, умноженные на коэффициент, с округлением до сотых."""
    return Nutrients(
        kcal=_round(source.kcal * factor),
        protein=_round(source.protein * factor),
        fat=_round(source.fat * factor),
        carbs=_round(source.carbs * factor),
    )


def portion(per_100g: HasNutrients, grams: Decimal) -> Nutrients:
    """КБЖУ порции по значениям на 100 г."""
    return scale(per_100g, grams / 100)


def total(items: Iterable[HasNutrients]) -> Nutrients:
    result = ZERO
    for item in items:
        result = Nutrients(
            kcal=result.kcal + item.kcal,
            protein=result.protein + item.protein,
            fat=result.fat + item.fat,
            carbs=result.carbs + item.carbs,
        )
    return result


@dataclass(frozen=True, slots=True)
class MealDay:
    meal_type: MealType
    items: list[MealItem]
    total: Nutrients


@dataclass(frozen=True, slots=True)
class Diary:
    date: date
    meals: list[MealDay]
    total: Nutrients


class NotFoundError(Exception):
    """Продукт или запись дневника не найдены (или принадлежат другому пользователю)."""


class WrongItemKindError(Exception):
    """Граммовку меняют у продукта, КБЖУ — у быстрой записи. Перепутали."""


async def search_foods(session: AsyncSession, user: User, query: str) -> list[Food]:
    """Поиск продуктов. Пустой запрос — недавно использованные."""
    query = query.strip()
    repo = FoodRepository(session)
    if not query:
        return await repo.recent(user.id, RECENT_LIMIT)
    return await repo.search(user.id, query, SEARCH_LIMIT)


async def list_favorites(session: AsyncSession, user: User) -> list[Food]:
    return await FoodRepository(session).favorites(user.id, FAVORITES_LIMIT)


async def favorite_ids(session: AsyncSession, user: User, foods: Iterable[Food]) -> set[int]:
    return await FoodRepository(session).favorite_ids(user.id, [f.id for f in foods])


async def set_favorite(session: AsyncSession, user: User, food_id: int, favorite: bool) -> None:
    """Отмечает продукт избранным или снимает отметку. Повторный вызов ничего не меняет."""
    repo = FoodRepository(session)
    if await repo.get_visible(user.id, food_id) is None:
        raise NotFoundError
    if favorite:
        await repo.add_favorite(user.id, food_id)
    else:
        await repo.remove_favorite(user.id, food_id)
    await session.commit()


async def create_food(session: AsyncSession, user: User, name: str, per_100g: Nutrients) -> Food:
    """Свой продукт. Виден только автору."""
    food = await FoodRepository(session).create(
        owner_id=user.id,
        name=name.strip(),
        kcal=per_100g.kcal,
        protein=per_100g.protein,
        fat=per_100g.fat,
        carbs=per_100g.carbs,
    )
    await session.commit()
    return food


async def get_diary(session: AsyncSession, user: User, day: date | None) -> Diary:
    """Все приёмы пищи за день — в фиксированном порядке, включая пустые."""
    day = day or user_today(user)
    meals = {m.meal_type: m for m in await MealRepository(session).list_for_day(user.id, day)}
    result = []
    for meal_type in MEAL_TYPES:
        items = meals[meal_type].items if meal_type in meals else []
        result.append(MealDay(meal_type=meal_type, items=items, total=total(items)))
    return Diary(date=day, meals=result, total=total(m.total for m in result))


async def add_item(
    session: AsyncSession,
    user: User,
    day: date | None,
    meal_type: MealType,
    food_id: int,
    grams: Decimal,
) -> MealItem:
    """Добавляет продукт в приём пищи. КБЖУ сохраняется снимком."""
    food = await FoodRepository(session).get_visible(user.id, food_id)
    if food is None:
        raise NotFoundError
    repo = MealRepository(session)
    meal = await repo.get_or_create(user.id, day or user_today(user), meal_type)
    n = portion(food, grams)
    item = await repo.add_item(
        MealItem(
            meal_id=meal.id,
            food_id=food.id,
            name=food.name,
            grams=grams,
            kcal=n.kcal,
            protein=n.protein,
            fat=n.fat,
            carbs=n.carbs,
        )
    )
    await session.commit()
    return item


async def add_quick_item(
    session: AsyncSession,
    user: User,
    day: date | None,
    meal_type: MealType,
    name: str,
    n: Nutrients,
) -> MealItem:
    """Быстрая запись: КБЖУ вручную, без продукта из справочника."""
    repo = MealRepository(session)
    meal = await repo.get_or_create(user.id, day or user_today(user), meal_type)
    item = await repo.add_item(
        MealItem(
            meal_id=meal.id,
            food_id=None,
            name=name.strip(),
            grams=None,
            kcal=n.kcal,
            protein=n.protein,
            fat=n.fat,
            carbs=n.carbs,
        )
    )
    await session.commit()
    return item


async def update_item_grams(
    session: AsyncSession, user: User, item_id: int, grams: Decimal
) -> MealItem:
    """Меняет граммовку. КБЖУ пересчитывается из снимка, справочник не читается."""
    item = await MealRepository(session).get_item(user.id, item_id)
    if item is None:
        raise NotFoundError
    if item.grams is None:
        raise WrongItemKindError
    n = scale(item, grams / item.grams)
    item.grams = grams
    item.kcal, item.protein, item.fat, item.carbs = n.kcal, n.protein, n.fat, n.carbs
    await session.commit()
    return item


async def update_quick_item(
    session: AsyncSession, user: User, item_id: int, name: str, n: Nutrients
) -> MealItem:
    """Меняет название и КБЖУ быстрой записи."""
    item = await MealRepository(session).get_item(user.id, item_id)
    if item is None:
        raise NotFoundError
    if item.grams is not None:
        raise WrongItemKindError
    item.name = name.strip()
    item.kcal, item.protein, item.fat, item.carbs = n.kcal, n.protein, n.fat, n.carbs
    await session.commit()
    return item


async def delete_item(session: AsyncSession, user: User, item_id: int) -> None:
    repo = MealRepository(session)
    item = await repo.get_item(user.id, item_id)
    if item is None:
        raise NotFoundError
    await repo.delete_item(item)
    await session.commit()
