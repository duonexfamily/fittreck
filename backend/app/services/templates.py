"""Шаблоны тренировок: сохранить тренировку как программу и повторить её в один клик."""

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import TemplateSet, User, Workout, WorkoutSet, WorkoutTemplate
from app.db.repositories.templates import TemplateRepository
from app.db.repositories.workouts import WorkoutRepository
from app.services.profile import user_today
from app.services.workouts import NotFoundError, WorkoutDetail, get_workout, group_sets

MAX_TEMPLATES = 50


@dataclass(frozen=True, slots=True)
class TemplateSummary:
    template: WorkoutTemplate
    exercise_names: list[str]
    set_count: int


class EmptyWorkoutError(Exception):
    """В тренировке нет подходов — шаблон сохранять не из чего."""


class TooManyTemplatesError(Exception):
    """Достигнут предел числа шаблонов."""


def _summary(template: WorkoutTemplate) -> TemplateSummary:
    names: list[str] = []
    for s in template.sets:
        if s.exercise.name not in names:
            names.append(s.exercise.name)
    return TemplateSummary(template=template, exercise_names=names, set_count=len(template.sets))


async def list_templates(session: AsyncSession, user: User) -> list[TemplateSummary]:
    return [_summary(t) for t in await TemplateRepository(session).list_all(user.id)]


async def create_template(
    session: AsyncSession, user: User, name: str, workout_id: int
) -> TemplateSummary:
    """Шаблон из тренировки: все подходы с их значениями, упражнения в том же порядке."""
    repo = TemplateRepository(session)
    workout = await WorkoutRepository(session).get(user.id, workout_id)
    if workout is None:
        raise NotFoundError
    if not workout.sets:
        raise EmptyWorkoutError
    if await repo.count(user.id) >= MAX_TEMPLATES:
        raise TooManyTemplatesError
    sets = [s for block in group_sets(workout.sets) for s in block.sets]
    template = await repo.add(
        WorkoutTemplate(
            user_id=user.id,
            name=name.strip(),
            sets=[
                TemplateSet(
                    exercise_id=s.exercise_id,
                    position=position,
                    reps=s.reps,
                    weight_kg=s.weight_kg,
                    duration_s=s.duration_s,
                    distance_m=s.distance_m,
                    exercise=s.exercise,
                )
                for position, s in enumerate(sets, start=1)
            ],
        )
    )
    await session.commit()
    return _summary(template)


async def delete_template(session: AsyncSession, user: User, template_id: int) -> None:
    repo = TemplateRepository(session)
    template = await repo.get(user.id, template_id)
    if template is None:
        raise NotFoundError
    await repo.delete(template)
    await session.commit()


async def start_template(
    session: AsyncSession, user: User, template_id: int, day: date | None
) -> WorkoutDetail:
    """Новая тренировка по шаблону. Подходы копируются невыполненными — их отмечают по ходу."""
    template = await TemplateRepository(session).get(user.id, template_id)
    if template is None:
        raise NotFoundError
    today = user_today(user)
    day = day or today
    set_no: dict[int, int] = {}
    sets = []
    for s in template.sets:
        set_no[s.exercise_id] = set_no.get(s.exercise_id, 0) + 1
        sets.append(
            WorkoutSet(
                exercise_id=s.exercise_id,
                set_no=set_no[s.exercise_id],
                reps=s.reps,
                weight_kg=s.weight_kg,
                duration_s=s.duration_s,
                distance_m=s.distance_m,
                done=False,
                exercise=s.exercise,
            )
        )
    workout = await WorkoutRepository(session).add(
        Workout(
            user_id=user.id,
            date=day,
            status="planned",
            started_at=datetime.now(UTC) if day == today else None,
            sets=sets,
        )
    )
    await session.commit()
    # Перечитываем: подходы и упражнения — в том же виде, что и у обычной тренировки
    return await get_workout(session, user, workout.id)
