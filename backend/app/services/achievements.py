"""Личные рекорды в упражнениях и достижения за всё время."""

from dataclasses import dataclass
from datetime import date

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories.stats import StatsRepository
from app.services.profile import user_today
from app.services.streaks import compute_streak

# Сколько рекордов показываем — самые свежие
RECORDS_LIMIT = 10


@dataclass(frozen=True, slots=True)
class Record:
    exercise: str
    weight_kg: float
    reps: int
    date: date


@dataclass(frozen=True, slots=True)
class Counters:
    active_days: int
    best_streak: int
    workouts: int
    checkins: int


@dataclass(frozen=True, slots=True)
class Achievement:
    key: str
    emoji: str
    title: str
    progress: int
    goal: int

    @property
    def achieved(self) -> bool:
        return self.progress >= self.goal


# (ключ, эмодзи, название, счётчик, цель) — от простого к сложному
ACHIEVEMENTS: tuple[tuple[str, str, str, str, int], ...] = (
    ("first_day", "🌱", "Первая запись", "active_days", 1),
    ("streak_3", "🔥", "3 дня подряд", "best_streak", 3),
    ("workouts_1", "🏋️", "Первая тренировка", "workouts", 1),
    ("checkins_7", "😴", "7 чек-инов", "checkins", 7),
    ("streak_7", "🔥", "Неделя подряд", "best_streak", 7),
    ("workouts_10", "💪", "10 тренировок", "workouts", 10),
    ("checkins_30", "🌙", "30 чек-инов", "checkins", 30),
    ("streak_30", "🏆", "Месяц подряд", "best_streak", 30),
    ("workouts_50", "🥇", "50 тренировок", "workouts", 50),
    ("days_100", "💯", "100 дней с записями", "active_days", 100),
)


def build_achievements(counters: Counters) -> list[Achievement]:
    """Прогресс не больше цели: «7 из 7», а не «12 из 7»."""
    return [
        Achievement(key, emoji, title, min(getattr(counters, counter), goal), goal)
        for key, emoji, title, counter, goal in ACHIEVEMENTS
    ]


async def get_records(session: AsyncSession, user: User) -> list[Record]:
    rows = await StatsRepository(session).exercise_records(user.id, RECORDS_LIMIT)
    return [Record(*row) for row in rows]


async def get_achievements(session: AsyncSession, user: User) -> list[Achievement]:
    repo = StatsRepository(session)
    # Все дни с записями: серия за всё время, а не только за последний год
    active = await repo.active_dates(user.id, date.min)
    streak = compute_streak(active, user_today(user))
    counters = Counters(
        active_days=len(active),
        best_streak=streak.best,
        workouts=await repo.count_done_workouts(user.id),
        checkins=await repo.count_checkins(user.id),
    )
    return build_achievements(counters)
