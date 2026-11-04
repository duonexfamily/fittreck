import importlib.util
from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.schemas.workouts import ExerciseIn, SetIn, WorkoutPatch
from app.main import app
from app.services.workouts import (
    EXERCISE_KINDS,
    MUSCLE_GROUPS,
    SetValues,
    WrongSetError,
    check_set,
    group_sets,
    set_volume,
    volume,
)

client = TestClient(app)


@pytest.mark.parametrize(
    ("kind", "values"),
    [
        ("strength", SetValues(reps=10, weight_kg=Decimal("60"))),
        ("strength", SetValues(reps=15)),  # без веса — отжимания, подтягивания
        ("cardio", SetValues(duration_s=1800)),
        ("cardio", SetValues(distance_m=5000)),
        ("cardio", SetValues(duration_s=1800, distance_m=5000)),
        ("stretch", SetValues(duration_s=60)),
    ],
)
def test_check_set_accepts(kind: str, values: SetValues) -> None:
    check_set(kind, values)


@pytest.mark.parametrize(
    ("kind", "values"),
    [
        ("strength", SetValues()),
        ("strength", SetValues(weight_kg=Decimal("60"))),
        ("strength", SetValues(reps=10, distance_m=100)),
        ("cardio", SetValues()),
        ("cardio", SetValues(reps=10, duration_s=60)),
        ("stretch", SetValues()),
        ("stretch", SetValues(duration_s=60, reps=1)),
        ("yoga", SetValues(duration_s=60)),
    ],
)
def test_check_set_rejects(kind: str, values: SetValues) -> None:
    with pytest.raises(WrongSetError):
        check_set(kind, values)


def test_volume() -> None:
    sets = [
        SetValues(reps=10, weight_kg=Decimal("60")),
        SetValues(reps=8, weight_kg=Decimal("62.5")),
        SetValues(reps=20),  # без веса не считается
        SetValues(duration_s=600),
    ]
    assert set_volume(sets[1]) == Decimal("500.0")
    assert volume(sets) == Decimal("1100.0")
    assert volume([]) == Decimal(0)


def _set(id_: int, exercise_id: int, set_no: int) -> Any:
    return SimpleNamespace(
        id=id_, exercise_id=exercise_id, set_no=set_no, exercise=f"ex{exercise_id}"
    )


def test_group_sets_keeps_order_of_first_set() -> None:
    sets = [_set(4, 1, 2), _set(1, 2, 1), _set(2, 1, 1), _set(3, 2, 2)]
    blocks = group_sets(sets)
    assert [str(b.exercise) for b in blocks] == ["ex2", "ex1"]
    assert [s.id for s in blocks[0].sets] == [1, 3]
    assert [s.id for s in blocks[1].sets] == [2, 4]


@pytest.mark.parametrize(
    "body",
    [
        {"exercise_id": 1, "reps": 0},
        {"exercise_id": 1, "reps": 1001},
        {"exercise_id": 1, "weight_kg": "-1"},
        {"exercise_id": 1, "weight_kg": "500.5"},
        {"exercise_id": 1, "weight_kg": "1.125"},
        {"exercise_id": 1, "duration_s": 0},
        {"exercise_id": 1, "distance_m": 0},
    ],
)
def test_set_in_rejects_out_of_range(body: dict[str, Any]) -> None:
    with pytest.raises(ValidationError):
        SetIn.model_validate(body)


def test_exercise_in_rejects_blank_and_unknown() -> None:
    with pytest.raises(ValidationError):
        ExerciseIn(name="  ", muscle_group="chest", kind="strength")
    with pytest.raises(ValidationError):
        ExerciseIn.model_validate({"name": "Жим", "muscle_group": "neck", "kind": "strength"})


def test_workout_patch() -> None:
    assert WorkoutPatch.model_validate({"rpe": None}).model_dump(exclude_unset=True) == {
        "rpe": None
    }
    for bad in ({}, {"status": None}, {"rpe": 0}, {"rpe": 11}, {"status": "skipped"}):
        with pytest.raises(ValidationError):
            WorkoutPatch.model_validate(bad)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/exercises"),
        ("post", "/api/v1/exercises"),
        ("get", "/api/v1/workouts"),
        ("post", "/api/v1/workouts"),
        ("get", "/api/v1/workouts/1"),
        ("patch", "/api/v1/workouts/1"),
        ("delete", "/api/v1/workouts/1"),
        ("post", "/api/v1/workouts/1/sets"),
        ("patch", "/api/v1/workout-sets/1"),
        ("delete", "/api/v1/workout-sets/1"),
    ],
)
def test_workout_endpoints_require_auth(method: str, path: str) -> None:
    assert client.request(method, path).status_code == 401


def _load_seed() -> list[tuple[str, str, str]]:
    path = next(Path(__file__).parent.parent.glob("migrations/versions/*_0009_seed_exercises.py"))
    spec = importlib.util.spec_from_file_location("seed_exercises", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.EXERCISES  # type: ignore[no-any-return]


def test_seed_exercises_are_consistent() -> None:
    exercises = _load_seed()
    names = [e[0] for e in exercises]
    assert len(names) == len(set(names)), "повторяющиеся названия"
    for name, muscle, kind in exercises:
        assert muscle in MUSCLE_GROUPS, name
        assert kind in EXERCISE_KINDS, name
        assert len(name) <= 128, name
