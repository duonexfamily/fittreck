"""Журнал веса."""

from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories.body_metrics import BodyMetricRepository
from app.services.profile import user_today

HISTORY_DAYS = 90


@dataclass(frozen=True, slots=True)
class WeightEntry:
    date: date
    weight_kg: Decimal


class NotFoundError(Exception):
    """Записи веса за этот день нет."""


class FutureDateError(Exception):
    """Вес на будущую дату."""


class LastEntryError(Exception):
    """Нельзя удалить единственную запись: без веса не посчитать норму КБЖУ."""


async def get_history(
    session: AsyncSession, user: User, days: int = HISTORY_DAYS
) -> list[WeightEntry]:
    """Вес за последние дни, от старых к новым."""
    since = user_today(user) - timedelta(days=days - 1)
    rows = await BodyMetricRepository(session).list_weights(user.id, since)
    return [WeightEntry(date=day, weight_kg=weight) for day, weight in rows]


async def log_weight(
    session: AsyncSession, user: User, day: date | None, weight_kg: Decimal
) -> WeightEntry:
    """Записывает вес за день. Повторная запись за тот же день заменяет прежнюю."""
    today = user_today(user)
    day = day or today
    if day > today:
        raise FutureDateError
    await BodyMetricRepository(session).upsert_weight(user.id, day, weight_kg)
    await session.commit()
    return WeightEntry(date=day, weight_kg=weight_kg)


async def delete_weight(session: AsyncSession, user: User, day: date) -> None:
    repo = BodyMetricRepository(session)
    if await repo.count_weights(user.id) <= 1:
        raise LastEntryError
    if not await repo.clear_weight(user.id, day):
        raise NotFoundError
    await session.commit()
