"""Серии дней подряд с записями — для мотивации на главном экране и в боте."""

from collections.abc import Set
from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories.stats import StatsRepository
from app.services.profile import user_today

# Сколько дней назад смотрим. Лучшая серия считается в этом окне
HISTORY_DAYS = 365
# Сколько последних дней показываем точками на главном экране
WEEK_DAYS = 7


@dataclass(frozen=True, slots=True)
class Streak:
    # Дней подряд по сегодня. Пока сегодня пусто, серия не прервана — считаем по вчера
    current: int
    best: int
    today_done: bool
    # Были ли записи за последние WEEK_DAYS дней, от старых к новым, последний — сегодня
    week: tuple[bool, ...]


def compute_streak(active: Set[date], today: date) -> Streak:
    """Считает серии по множеству активных дней. Дни после today не учитываются."""
    today_done = today in active
    current = 0
    day = today if today_done else today - timedelta(days=1)
    while day in active:
        current += 1
        day -= timedelta(days=1)

    best = run = 0
    previous: date | None = None
    for day in sorted(d for d in active if d <= today):
        run = run + 1 if previous is not None and day - previous == timedelta(days=1) else 1
        best = max(best, run)
        previous = day

    week = tuple(today - timedelta(days=i) in active for i in range(WEEK_DAYS - 1, -1, -1))
    return Streak(current=current, best=best, today_done=today_done, week=week)


def days_word(n: int) -> str:
    """1 день, 2 дня, 5 дней, 11 дней, 21 день."""
    if n % 10 == 1 and n % 100 != 11:
        return "день"
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return "дня"
    return "дней"


async def get_streak(session: AsyncSession, user: User) -> Streak:
    today = user_today(user)
    since = today - timedelta(days=HISTORY_DAYS - 1)
    active = await StatsRepository(session).active_dates(user.id, since)
    return compute_streak(active, today)
