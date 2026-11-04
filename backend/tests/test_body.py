from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.schemas.body import WaterIn, WeightIn
from app.main import app
from app.services.nutrition_calc import WATER_DEFAULT_ML, calc_water_ml

client = TestClient(app)


@pytest.mark.parametrize(
    ("weight", "expected"),
    [
        (70.0, 2000),  # 2100 → ближайший стакан
        (80.0, 2500),  # 2400 → 2500
        (40.0, 1500),  # нижняя граница
        (150.0, 3500),  # верхняя граница
    ],
)
def test_calc_water_ml(weight: float, expected: int) -> None:
    assert calc_water_ml(weight) == expected


def test_calc_water_ml_without_weight() -> None:
    assert calc_water_ml(None) == WATER_DEFAULT_ML


@pytest.mark.parametrize("value", ["29.9", "300.1", "70.25"])
def test_weight_in_rejects_bad_values(value: str) -> None:
    with pytest.raises(ValidationError):
        WeightIn(weight_kg=Decimal(value))


@pytest.mark.parametrize("delta", [0, 2001, -2001])
def test_water_in_rejects_bad_delta(delta: int) -> None:
    with pytest.raises(ValidationError):
        WaterIn(delta_ml=delta)


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/weight"),
        ("put", "/api/v1/weight"),
        ("delete", "/api/v1/weight/2026-11-04"),
        ("get", "/api/v1/water"),
        ("post", "/api/v1/water"),
    ],
)
def test_body_endpoints_require_auth(method: str, path: str) -> None:
    assert client.request(method, path).status_code == 401
