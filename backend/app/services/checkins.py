"""Ежедневные чек-ины: сон, энергия, стресс, настроение."""

from dataclasses import asdict, dataclass
from datetime import date, time, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Checkin, User
from app.db.repositories.checkins import CheckinRepository
from app.services.profile import user_today

# Самый длинный период за один запрос — год с запасом на високосный
MAX_RANGE_DAYS = 366
DEFAULT_RANGE_DAYS = 30
# Оценки, которые можно поставить кнопками в чате бота, по порядку вопросов
QUICK_FIELDS = ("sleep_quality", "energy", "mood")


@dataclass(frozen=True, slots=True)
class CheckinValues:
    """Поля чек-ина. None — не указано. Оценки 1–5."""

    bed_time: time | None = None
    wake_time: time | None = None
    sleep_quality: int | None = None
    energy: int | None = None
    stress: int | None = None
    mood: int | None = None
    note: str | None = None


class FutureDateError(Exception):
    """Чек-ин на будущую дату."""


class RangeError(Exception):
    """Период задан неверно: конец раньше начала или слишком длинный."""


def sleep_minutes(bed: time | None, wake: time | None) -> int | None:
    """Длительность сна по времени на часах. Отход позже подъёма — значит, накануне вечером."""
    if bed is None or wake is None:
        return None
    minutes = (wake.hour * 60 + wake.minute) - (bed.hour * 60 + bed.minute)
    return minutes % (24 * 60)


async def list_checkins(
    session: AsyncSession, user: User, date_from: date | None, date_to: date | None
) -> list[Checkin]:
    """Чек-ины за период, от старых к новым. По умолчанию — последние 30 дней."""
    date_to = date_to or user_today(user)
    date_from = date_from or date_to - timedelta(days=DEFAULT_RANGE_DAYS - 1)
    if date_from > date_to or (date_to - date_from).days >= MAX_RANGE_DAYS:
        raise RangeError
    return await CheckinRepository(session).list_range(user.id, date_from, date_to)


async def save_checkin(
    session: AsyncSession, user: User, day: date, values: CheckinValues
) -> Checkin:
    """Записывает чек-ин за день целиком. Время — до минуты, пустая заметка — NULL."""
    if day > user_today(user):
        raise FutureDateError
    fields = asdict(values)
    for key in ("bed_time", "wake_time"):
        if fields[key] is not None:
            fields[key] = fields[key].replace(second=0, microsecond=0)
    if fields["note"] is not None:
        fields["note"] = fields["note"].strip() or None
    checkin = await CheckinRepository(session).upsert(user.id, day, fields)
    await session.commit()
    return checkin


async def save_quick(
    session: AsyncSession, user: User, day: date, field: str, value: int
) -> Checkin:
    """Ставит одну оценку из бота. Остальные поля чек-ина за день не меняются."""
    if field not in QUICK_FIELDS or not 1 <= value <= 5:
        raise ValueError(field)
    if day > user_today(user):
        raise FutureDateError
    checkin = await CheckinRepository(session).upsert(user.id, day, {field: value})
    await session.commit()
    return checkin
