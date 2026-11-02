from datetime import date, datetime
from decimal import Decimal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import BaseModel, ConfigDict, Field, field_validator

from app.services.nutrition_calc import Activity, Goal, Sex

MIN_AGE = 14
MAX_AGE = 100


class MeOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    telegram_id: int
    first_name: str
    username: str | None
    sex: str | None
    birth_date: date | None
    height_cm: int | None
    goal: str | None
    activity_level: str | None
    timezone: str
    onboarded_at: datetime | None


class ProfileIn(BaseModel):
    sex: Sex
    birth_date: date
    height_cm: int = Field(ge=100, le=250)
    weight_kg: Decimal = Field(ge=30, le=300, decimal_places=2)
    goal: Goal
    activity_level: Activity
    timezone: str = Field(max_length=64)

    @field_validator("birth_date")
    @classmethod
    def _check_age(cls, value: date) -> date:
        today = date.today()
        age = today.year - value.year - ((today.month, today.day) < (value.month, value.day))
        if not MIN_AGE <= age <= MAX_AGE:
            raise ValueError(f"возраст должен быть от {MIN_AGE} до {MAX_AGE} лет")
        return value

    @field_validator("timezone")
    @classmethod
    def _check_timezone(cls, value: str) -> str:
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError("неизвестный часовой пояс") from exc
        return value


class TargetsOut(BaseModel):
    weight_kg: Decimal
    bmr: int
    tdee: int
    kcal: int
    protein_g: int
    fat_g: int
    carbs_g: int
