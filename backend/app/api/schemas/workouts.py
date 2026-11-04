import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.workouts import ExerciseKind, MuscleGroup, WorkoutStatus


class ExerciseOut(BaseModel):
    """own — упражнение добавлено пользователем."""

    id: int
    name: str
    muscle_group: MuscleGroup
    kind: ExerciseKind
    own: bool


class ExerciseIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    muscle_group: MuscleGroup
    kind: ExerciseKind

    @model_validator(mode="after")
    def _check_name(self) -> "ExerciseIn":
        if not self.name.strip():
            raise ValueError("название не может быть пустым")
        return self


class SetValuesIn(BaseModel):
    """Значения подхода. Какие поля нужны — зависит от вида упражнения, проверяет сервис."""

    reps: int | None = Field(default=None, ge=1, le=1000)
    weight_kg: Decimal | None = Field(default=None, ge=0, le=500, decimal_places=2)
    duration_s: int | None = Field(default=None, ge=1, le=86400)
    distance_m: int | None = Field(default=None, ge=1, le=1_000_000)


class SetIn(SetValuesIn):
    exercise_id: int


class SetOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    exercise_id: int
    set_no: int
    reps: int | None
    weight_kg: float | None
    duration_s: int | None
    distance_m: int | None


class ExerciseBlockOut(BaseModel):
    exercise: ExerciseOut
    sets: list[SetOut]


class WorkoutIn(BaseModel):
    # Без даты — сегодня в часовом поясе пользователя
    date: dt.date | None = None


class WorkoutPatch(BaseModel):
    """Передаются только меняемые поля. rpe/note = null — очистить."""

    status: WorkoutStatus | None = None
    rpe: int | None = Field(default=None, ge=1, le=10)
    note: str | None = Field(default=None, max_length=1000)

    @model_validator(mode="after")
    def _check(self) -> "WorkoutPatch":
        if "status" in self.model_fields_set and self.status is None:
            raise ValueError("статус не может быть пустым")
        if not self.model_fields_set:
            raise ValueError("нечего менять")
        return self


class WorkoutOut(BaseModel):
    id: int
    date: dt.date
    status: WorkoutStatus
    started_at: dt.datetime | None
    finished_at: dt.datetime | None
    rpe: int | None
    note: str | None
    exercises: list[ExerciseBlockOut]
    volume_kg: float


class WorkoutSummaryOut(BaseModel):
    id: int
    date: dt.date
    status: WorkoutStatus
    rpe: int | None
    exercise_names: list[str]
    set_count: int
    volume_kg: float
