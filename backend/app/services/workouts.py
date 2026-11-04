"""Тренировки: каталог упражнений, тренировки, подходы, объём."""

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Literal, TypedDict, get_args

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import Exercise, User, Workout, WorkoutSet
from app.db.repositories.exercises import ExerciseRepository
from app.db.repositories.workouts import WorkoutRepository
from app.services.profile import user_today

MuscleGroup = Literal["chest", "back", "shoulders", "arms", "legs", "core", "full_body"]
ExerciseKind = Literal["strength", "cardio", "stretch"]
WorkoutStatus = Literal["planned", "done"]
MUSCLE_GROUPS: tuple[MuscleGroup, ...] = get_args(MuscleGroup)
EXERCISE_KINDS: tuple[ExerciseKind, ...] = get_args(ExerciseKind)

SEARCH_LIMIT = 200
# Самый длинный период за один запрос — год с запасом на високосный
MAX_RANGE_DAYS = 366
DEFAULT_RANGE_DAYS = 30


@dataclass(frozen=True, slots=True)
class SetValues:
    reps: int | None = None
    weight_kg: Decimal | None = None
    duration_s: int | None = None
    distance_m: int | None = None


@dataclass(frozen=True, slots=True)
class ExerciseBlock:
    """Упражнение в тренировке и его подходы по порядку."""

    exercise: Exercise
    sets: list[WorkoutSet]


@dataclass(frozen=True, slots=True)
class WorkoutDetail:
    workout: Workout
    exercises: list[ExerciseBlock]
    volume_kg: Decimal


@dataclass(frozen=True, slots=True)
class WorkoutSummary:
    workout: Workout
    exercise_names: list[str]
    set_count: int
    volume_kg: Decimal


class WorkoutChanges(TypedDict, total=False):
    """Изменяемые поля тренировки. Нет ключа — поле не меняется, None — очистить."""

    status: WorkoutStatus
    rpe: int | None
    note: str | None


class NotFoundError(Exception):
    """Упражнение, тренировка или подход не найдены (или принадлежат другому пользователю)."""


class WrongSetError(Exception):
    """Поля подхода не подходят виду упражнения. Текст — для пользователя."""


class RangeError(Exception):
    """Период задан неверно: конец раньше начала или слишком длинный."""


def check_set(kind: str, values: SetValues) -> None:
    """Подход силового — повторения (и вес), кардио — время и/или дистанция, на время — время."""
    filled = {name for name in SetValues.__slots__ if getattr(values, name) is not None}
    if kind == "strength":
        ok = values.reps is not None and filled <= {"reps", "weight_kg"}
        message = "укажите повторения, вес — по желанию"
    elif kind == "cardio":
        ok = bool(filled) and filled <= {"duration_s", "distance_m"}
        message = "укажите время или дистанцию"
    elif kind == "stretch":
        ok = filled == {"duration_s"}
        message = "укажите время"
    else:
        ok, message = False, "неизвестный вид упражнения"
    if not ok:
        raise WrongSetError(message)


def set_volume(s: WorkoutSet | SetValues) -> Decimal:
    """Тоннаж подхода: повторения × вес. Без веса или без повторений — 0."""
    if s.reps is None or s.weight_kg is None:
        return Decimal(0)
    return s.reps * s.weight_kg


def volume(sets: Iterable[WorkoutSet | SetValues]) -> Decimal:
    return sum((set_volume(s) for s in sets), Decimal(0))


def group_sets(sets: Iterable[WorkoutSet]) -> list[ExerciseBlock]:
    """Подходы по упражнениям. Упражнения — в порядке первого подхода, подходы — по номеру."""
    blocks: dict[int, ExerciseBlock] = {}
    for s in sorted(sets, key=lambda s: s.id):
        if s.exercise_id not in blocks:
            blocks[s.exercise_id] = ExerciseBlock(exercise=s.exercise, sets=[])
        blocks[s.exercise_id].sets.append(s)
    for block in blocks.values():
        block.sets.sort(key=lambda s: (s.set_no, s.id))
    return list(blocks.values())


def _detail(workout: Workout) -> WorkoutDetail:
    return WorkoutDetail(
        workout=workout, exercises=group_sets(workout.sets), volume_kg=volume(workout.sets)
    )


async def search_exercises(
    session: AsyncSession,
    user: User,
    query: str,
    muscle_group: MuscleGroup | None,
    kind: ExerciseKind | None,
) -> list[Exercise]:
    return await ExerciseRepository(session).search(
        user.id, query.strip(), muscle_group, kind, SEARCH_LIMIT
    )


async def create_exercise(
    session: AsyncSession, user: User, name: str, muscle_group: MuscleGroup, kind: ExerciseKind
) -> Exercise:
    """Своё упражнение. Видно только автору."""
    exercise = await ExerciseRepository(session).create(user.id, name.strip(), muscle_group, kind)
    await session.commit()
    return exercise


async def list_workouts(
    session: AsyncSession, user: User, date_from: date | None, date_to: date | None
) -> list[WorkoutSummary]:
    """Тренировки за период, новые сверху. По умолчанию — последние 30 дней."""
    date_to = date_to or user_today(user)
    date_from = date_from or date_to - timedelta(days=DEFAULT_RANGE_DAYS - 1)
    if date_from > date_to or (date_to - date_from).days >= MAX_RANGE_DAYS:
        raise RangeError
    workouts = await WorkoutRepository(session).list_range(user.id, date_from, date_to)
    result = []
    for w in workouts:
        blocks = group_sets(w.sets)
        result.append(
            WorkoutSummary(
                workout=w,
                exercise_names=[b.exercise.name for b in blocks],
                set_count=len(w.sets),
                volume_kg=volume(w.sets),
            )
        )
    return result


async def create_workout(session: AsyncSession, user: User, day: date | None) -> WorkoutDetail:
    """Новая незавершённая тренировка. Начатая сегодня получает время начала."""
    today = user_today(user)
    day = day or today
    workout = await WorkoutRepository(session).add(
        Workout(
            user_id=user.id,
            date=day,
            status="planned",
            started_at=datetime.now(UTC) if day == today else None,
            sets=[],
        )
    )
    await session.commit()
    return WorkoutDetail(workout=workout, exercises=[], volume_kg=Decimal(0))


async def _get(session: AsyncSession, user: User, workout_id: int) -> Workout:
    workout = await WorkoutRepository(session).get(user.id, workout_id)
    if workout is None:
        raise NotFoundError
    return workout


async def get_workout(session: AsyncSession, user: User, workout_id: int) -> WorkoutDetail:
    return _detail(await _get(session, user, workout_id))


async def update_workout(
    session: AsyncSession, user: User, workout_id: int, changes: WorkoutChanges
) -> WorkoutDetail:
    """Статус, RPE, заметка. Завершение фиксирует время окончания, возврат в план — сбрасывает."""
    workout = await _get(session, user, workout_id)
    if "status" in changes and changes["status"] != workout.status:
        workout.status = changes["status"]
        workout.finished_at = datetime.now(UTC) if workout.status == "done" else None
    if "rpe" in changes:
        workout.rpe = changes["rpe"]
    if "note" in changes:
        note = changes["note"]
        # Пустая заметка хранится как NULL
        workout.note = (note.strip() or None) if note is not None else None
    await session.commit()
    return _detail(workout)


async def delete_workout(session: AsyncSession, user: User, workout_id: int) -> None:
    repo = WorkoutRepository(session)
    workout = await _get(session, user, workout_id)
    await repo.delete(workout)
    await session.commit()


async def add_set(
    session: AsyncSession, user: User, workout_id: int, exercise_id: int, values: SetValues
) -> WorkoutSet:
    """Подход в конец упражнения. Первый подход добавляет упражнение в тренировку."""
    workout = await _get(session, user, workout_id)
    exercise = await ExerciseRepository(session).get_visible(user.id, exercise_id)
    if exercise is None:
        raise NotFoundError
    check_set(exercise.kind, values)
    repo = WorkoutRepository(session)
    existing = await repo.exercise_sets(workout.id, exercise.id)
    item = await repo.add_set(
        WorkoutSet(
            workout_id=workout.id,
            exercise_id=exercise.id,
            set_no=max((s.set_no for s in existing), default=0) + 1,
            reps=values.reps,
            weight_kg=values.weight_kg,
            duration_s=values.duration_s,
            distance_m=values.distance_m,
            exercise=exercise,
        )
    )
    await session.commit()
    return item


async def update_set(
    session: AsyncSession, user: User, set_id: int, values: SetValues
) -> WorkoutSet:
    """Заменяет значения подхода целиком."""
    item = await WorkoutRepository(session).get_set(user.id, set_id)
    if item is None:
        raise NotFoundError
    check_set(item.exercise.kind, values)
    item.reps, item.weight_kg = values.reps, values.weight_kg
    item.duration_s, item.distance_m = values.duration_s, values.distance_m
    await session.commit()
    return item


async def delete_set(session: AsyncSession, user: User, set_id: int) -> None:
    """Удаляет подход. Оставшиеся подходы упражнения нумеруются заново без пропусков."""
    repo = WorkoutRepository(session)
    item = await repo.get_set(user.id, set_id)
    if item is None:
        raise NotFoundError
    workout_id, exercise_id = item.workout_id, item.exercise_id
    await repo.delete_set(item)
    for no, s in enumerate(await repo.exercise_sets(workout_id, exercise_id), start=1):
        s.set_no = no
    await session.commit()
