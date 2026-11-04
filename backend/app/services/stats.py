"""Данные для графиков прогресса: по строке на каждый день периода."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Checkin, User
from app.db.repositories.checkins import CheckinRepository
from app.db.repositories.stats import StatsRepository
from app.services.checkins import sleep_minutes
from app.services.profile import user_today

# Периоды на экране «Прогресс», дней. ALL_TIME — с первой записи
ALL_TIME = 0
PERIODS = (7, 30, 90, ALL_TIME)
# «Всё время» — не дольше трёх лет: дальше график нечитаем, а ответ тяжёлый
MAX_ALL_TIME_DAYS = 3 * 365


@dataclass(frozen=True, slots=True)
class DayStats:
    """Итоги дня. None — за день нет данных, график рисует разрыв, а не ноль."""

    date: date
    weight_kg: float | None = None
    kcal: float | None = None
    sleep_minutes: int | None = None
    sleep_quality: int | None = None
    energy: int | None = None
    stress: int | None = None
    mood: int | None = None
    workouts: int = 0
    volume_kg: float = 0


def build_summary(
    date_from: date,
    date_to: date,
    weight: Mapping[date, float],
    kcal: Mapping[date, float],
    checkins: Sequence[Checkin],
    workouts: Mapping[date, tuple[int, float]],
) -> list[DayStats]:
    """Сводит данные в непрерывный ряд дней от старых к новым."""
    by_day = {c.date: c for c in checkins}
    result: list[DayStats] = []
    day = date_from
    while day <= date_to:
        c = by_day.get(day)
        count, volume = workouts.get(day, (0, 0.0))
        result.append(
            DayStats(
                date=day,
                weight_kg=weight.get(day),
                kcal=round(kcal[day]) if day in kcal else None,
                sleep_minutes=sleep_minutes(c.bed_time, c.wake_time) if c else None,
                sleep_quality=c.sleep_quality if c else None,
                energy=c.energy if c else None,
                stress=c.stress if c else None,
                mood=c.mood if c else None,
                workouts=count,
                volume_kg=round(volume, 1),
            )
        )
        day += timedelta(days=1)
    return result


async def period_start(session: AsyncSession, user: User, days: int, today: date) -> date:
    """Первый день периода. Для «всего времени» — день первой записи (без записей — 30 дней)."""
    if days not in PERIODS:
        raise ValueError(days)
    if days != ALL_TIME:
        return today - timedelta(days=days - 1)
    earliest = today - timedelta(days=MAX_ALL_TIME_DAYS - 1)
    active = await StatsRepository(session).active_dates(user.id, earliest)
    return min(active) if active else today - timedelta(days=29)


async def get_summary(session: AsyncSession, user: User, days: int) -> list[DayStats]:
    """Итоги за последние days дней, включая сегодня. ALL_TIME — с первой записи."""
    if days not in PERIODS:
        raise ValueError(days)
    date_to = user_today(user)
    date_from = await period_start(session, user, days, date_to)
    repo = StatsRepository(session)
    return build_summary(
        date_from,
        date_to,
        weight=await repo.daily_weight(user.id, date_from, date_to),
        kcal=await repo.daily_kcal(user.id, date_from, date_to),
        checkins=await CheckinRepository(session).list_range(user.id, date_from, date_to),
        workouts=await repo.daily_workouts(user.id, date_from, date_to),
    )
