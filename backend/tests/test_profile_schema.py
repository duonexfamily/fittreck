from datetime import date
from typing import Any

import pytest
from pydantic import ValidationError

from app.api.schemas.me import ProfileIn

VALID: dict[str, Any] = {
    "sex": "male",
    "birth_date": "1995-06-15",
    "height_cm": 180,
    "weight_kg": "80.5",
    "goal": "maintain",
    "activity_level": "moderate",
    "timezone": "Europe/Moscow",
}


def test_valid_profile() -> None:
    p = ProfileIn(**VALID)
    assert p.birth_date == date(1995, 6, 15)


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("sex", "other"),
        ("height_cm", 50),
        ("height_cm", 300),
        ("weight_kg", 10),
        ("weight_kg", "80.123"),
        ("goal", "fly"),
        ("activity_level", "extreme"),
        ("timezone", "Mars/Olympus"),
        ("timezone", "../../etc/passwd"),
        ("birth_date", "2024-01-01"),  # слишком молод
        ("birth_date", "1900-01-01"),  # слишком стар
    ],
)
def test_invalid_profile(field: str, value: Any) -> None:
    with pytest.raises(ValidationError):
        ProfileIn(**{**VALID, field: value})
