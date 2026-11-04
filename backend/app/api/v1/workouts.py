from datetime import date
from typing import Annotated, cast

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas.workouts import (
    ExerciseBlockOut,
    ExerciseIn,
    ExerciseOut,
    SetIn,
    SetOut,
    SetPatch,
    SetValuesIn,
    TemplateIn,
    TemplateOut,
    TemplateStartIn,
    WorkoutIn,
    WorkoutOut,
    WorkoutPatch,
    WorkoutSummaryOut,
)
from app.db.models import Exercise, WorkoutSet
from app.services import templates, workouts
from app.services.templates import EmptyWorkoutError, TemplateSummary, TooManyTemplatesError
from app.services.workouts import (
    ExerciseKind,
    MuscleGroup,
    NotFoundError,
    RangeError,
    SetValues,
    WorkoutChanges,
    WorkoutDetail,
    WrongSetError,
)

router = APIRouter(tags=["workouts"])


def _exercise_out(exercise: Exercise) -> ExerciseOut:
    # Чужие упражнения не видны, поэтому любое упражнение с владельцем — своё
    return ExerciseOut(
        id=exercise.id,
        name=exercise.name,
        muscle_group=cast(MuscleGroup, exercise.muscle_group),
        kind=cast(ExerciseKind, exercise.kind),
        own=exercise.owner_id is not None,
    )


def _workout_out(d: WorkoutDetail) -> WorkoutOut:
    w = d.workout
    return WorkoutOut(
        id=w.id,
        date=w.date,
        status=cast(workouts.WorkoutStatus, w.status),
        started_at=w.started_at,
        finished_at=w.finished_at,
        rpe=w.rpe,
        note=w.note,
        exercises=[
            ExerciseBlockOut(
                exercise=_exercise_out(b.exercise),
                sets=[SetOut.model_validate(s) for s in b.sets],
            )
            for b in d.exercises
        ],
        volume_kg=float(d.volume_kg),
    )


def _values(body: SetValuesIn) -> SetValues:
    return SetValues(
        reps=body.reps,
        weight_kg=body.weight_kg,
        duration_s=body.duration_s,
        distance_m=body.distance_m,
    )


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


def _wrong_set(exc: WrongSetError) -> HTTPException:
    return HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=str(exc))


@router.get("/exercises", response_model=list[ExerciseOut])
async def get_exercises(
    user: CurrentUser,
    session: SessionDep,
    query: Annotated[str, Query(max_length=64)] = "",
    muscle: MuscleGroup | None = None,
    kind: ExerciseKind | None = None,
) -> list[ExerciseOut]:
    found = await workouts.search_exercises(session, user, query, muscle, kind)
    return [_exercise_out(e) for e in found]


@router.post("/exercises", response_model=ExerciseOut, status_code=status.HTTP_201_CREATED)
async def post_exercise(body: ExerciseIn, user: CurrentUser, session: SessionDep) -> ExerciseOut:
    exercise = await workouts.create_exercise(
        session, user, body.name, body.muscle_group, body.kind
    )
    return _exercise_out(exercise)


@router.get("/workouts", response_model=list[WorkoutSummaryOut])
async def get_workouts(
    user: CurrentUser,
    session: SessionDep,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> list[WorkoutSummaryOut]:
    try:
        found = await workouts.list_workouts(session, user, date_from, date_to)
    except RangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Период — от 1 до {workouts.MAX_RANGE_DAYS} дней",
        ) from exc
    return [
        WorkoutSummaryOut(
            id=s.workout.id,
            date=s.workout.date,
            status=cast(workouts.WorkoutStatus, s.workout.status),
            rpe=s.workout.rpe,
            exercise_names=s.exercise_names,
            set_count=s.set_count,
            volume_kg=float(s.volume_kg),
        )
        for s in found
    ]


@router.post("/workouts", response_model=WorkoutOut, status_code=status.HTTP_201_CREATED)
async def post_workout(body: WorkoutIn, user: CurrentUser, session: SessionDep) -> WorkoutOut:
    return _workout_out(await workouts.create_workout(session, user, body.date))


@router.get("/workouts/{workout_id}", response_model=WorkoutOut)
async def get_workout(workout_id: int, user: CurrentUser, session: SessionDep) -> WorkoutOut:
    try:
        return _workout_out(await workouts.get_workout(session, user, workout_id))
    except NotFoundError as exc:
        raise _not_found("Тренировка не найдена") from exc


@router.patch("/workouts/{workout_id}", response_model=WorkoutOut)
async def patch_workout(
    workout_id: int, body: WorkoutPatch, user: CurrentUser, session: SessionDep
) -> WorkoutOut:
    # Только переданные поля: отсутствие и null различаются
    changes = cast(WorkoutChanges, body.model_dump(exclude_unset=True))
    try:
        return _workout_out(await workouts.update_workout(session, user, workout_id, changes))
    except NotFoundError as exc:
        raise _not_found("Тренировка не найдена") from exc


@router.delete("/workouts/{workout_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_workout(workout_id: int, user: CurrentUser, session: SessionDep) -> Response:
    try:
        await workouts.delete_workout(session, user, workout_id)
    except NotFoundError as exc:
        raise _not_found("Тренировка не найдена") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/workouts/{workout_id}/sets", response_model=SetOut, status_code=status.HTTP_201_CREATED
)
async def post_set(
    workout_id: int, body: SetIn, user: CurrentUser, session: SessionDep
) -> WorkoutSet:
    try:
        return await workouts.add_set(session, user, workout_id, body.exercise_id, _values(body))
    except NotFoundError as exc:
        raise _not_found("Тренировка или упражнение не найдены") from exc
    except WrongSetError as exc:
        raise _wrong_set(exc) from exc


@router.patch("/workout-sets/{set_id}", response_model=SetOut)
async def patch_set(
    set_id: int, body: SetPatch, user: CurrentUser, session: SessionDep
) -> WorkoutSet:
    try:
        return await workouts.update_set(session, user, set_id, _values(body), body.done)
    except NotFoundError as exc:
        raise _not_found("Подход не найден") from exc
    except WrongSetError as exc:
        raise _wrong_set(exc) from exc


@router.delete("/workout-sets/{set_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_set(set_id: int, user: CurrentUser, session: SessionDep) -> Response:
    try:
        await workouts.delete_set(session, user, set_id)
    except NotFoundError as exc:
        raise _not_found("Подход не найден") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


def _template_out(t: TemplateSummary) -> TemplateOut:
    return TemplateOut(
        id=t.template.id,
        name=t.template.name,
        exercise_names=t.exercise_names,
        set_count=t.set_count,
    )


@router.get("/templates", response_model=list[TemplateOut])
async def get_templates(user: CurrentUser, session: SessionDep) -> list[TemplateOut]:
    return [_template_out(t) for t in await templates.list_templates(session, user)]


@router.post("/templates", response_model=TemplateOut, status_code=status.HTTP_201_CREATED)
async def post_template(body: TemplateIn, user: CurrentUser, session: SessionDep) -> TemplateOut:
    try:
        return _template_out(
            await templates.create_template(session, user, body.name, body.workout_id)
        )
    except NotFoundError as exc:
        raise _not_found("Тренировка не найдена") from exc
    except EmptyWorkoutError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="В тренировке нет подходов",
        ) from exc
    except TooManyTemplatesError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Не больше {templates.MAX_TEMPLATES} шаблонов",
        ) from exc


@router.delete("/templates/{template_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_template(template_id: int, user: CurrentUser, session: SessionDep) -> Response:
    try:
        await templates.delete_template(session, user, template_id)
    except NotFoundError as exc:
        raise _not_found("Шаблон не найден") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post(
    "/templates/{template_id}/start",
    response_model=WorkoutOut,
    status_code=status.HTTP_201_CREATED,
)
async def start_template(
    template_id: int, body: TemplateStartIn, user: CurrentUser, session: SessionDep
) -> WorkoutOut:
    try:
        return _workout_out(await templates.start_template(session, user, template_id, body.date))
    except NotFoundError as exc:
        raise _not_found("Шаблон не найден") from exc
