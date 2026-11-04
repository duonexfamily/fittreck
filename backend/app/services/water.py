"""Учёт воды за день."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories.body_metrics import BodyMetricRepository
from app.db.repositories.water import WaterRepository
from app.services.nutrition_calc import calc_water_ml
from app.services.profile import user_today


@dataclass(frozen=True, slots=True)
class WaterDay:
    date: date
    ml: int
    target_ml: int


async def _target_ml(session: AsyncSession, user: User) -> int:
    weight = await BodyMetricRepository(session).latest_weight(user.id)
    return calc_water_ml(float(weight) if weight is not None else None)


async def get_day(session: AsyncSession, user: User, day: date | None) -> WaterDay:
    day = day or user_today(user)
    ml = await WaterRepository(session).get_ml(user.id, day)
    return WaterDay(date=day, ml=ml, target_ml=await _target_ml(session, user))


async def add(session: AsyncSession, user: User, day: date | None, delta_ml: int) -> WaterDay:
    """Добавляет воду за день. Отрицательное значение — отмена лишнего."""
    day = day or user_today(user)
    ml = await WaterRepository(session).add_ml(user.id, day, delta_ml)
    await session.commit()
    return WaterDay(date=day, ml=ml, target_ml=await _target_ml(session, user))
