from dataclasses import dataclass
from datetime import UTC, date, datetime
from decimal import Decimal
from typing import cast, get_args
from zoneinfo import ZoneInfo

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories.body_metrics import BodyMetricRepository
from app.services.nutrition_calc import Activity, Goal, Sex, Targets, age_on, calc_targets


@dataclass(frozen=True, slots=True)
class ProfileData:
    sex: Sex
    birth_date: date
    height_cm: int
    weight_kg: Decimal
    goal: Goal
    activity_level: Activity
    timezone: str


@dataclass(frozen=True, slots=True)
class UserTargets:
    weight_kg: Decimal
    targets: Targets


def user_today(user: User) -> date:
    """Сегодняшняя дата в часовом поясе пользователя."""
    return datetime.now(ZoneInfo(user.timezone)).date()


async def save_profile(session: AsyncSession, user: User, data: ProfileData) -> None:
    """Сохраняет анкету и вес на сегодня."""
    user.sex = data.sex
    user.birth_date = data.birth_date
    user.height_cm = data.height_cm
    user.goal = data.goal
    user.activity_level = data.activity_level
    user.timezone = data.timezone
    if user.onboarded_at is None:
        user.onboarded_at = datetime.now(UTC)

    await BodyMetricRepository(session).upsert_weight(user.id, user_today(user), data.weight_kg)
    await session.commit()


async def get_targets(session: AsyncSession, user: User) -> UserTargets | None:
    """Норма КБЖУ по анкете и последнему весу. None — анкета не заполнена."""
    if (
        user.onboarded_at is None
        or user.sex not in get_args(Sex)
        or user.birth_date is None
        or user.height_cm is None
        or user.goal not in get_args(Goal)
        or user.activity_level not in get_args(Activity)
    ):
        return None

    weight = await BodyMetricRepository(session).latest_weight(user.id)
    if weight is None:
        return None

    targets = calc_targets(
        # Значения проверены выше — cast только для mypy
        sex=cast(Sex, user.sex),
        weight_kg=float(weight),
        height_cm=user.height_cm,
        age=age_on(user.birth_date, user_today(user)),
        activity=cast(Activity, user.activity_level),
        goal=cast(Goal, user.goal),
    )
    return UserTargets(weight_kg=weight, targets=targets)
