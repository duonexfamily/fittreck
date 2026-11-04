import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class WeightEntryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: dt.date
    weight_kg: float


class WeightIn(BaseModel):
    # Без даты — сегодня в часовом поясе пользователя
    date: dt.date | None = None
    weight_kg: Decimal = Field(ge=30, le=300, decimal_places=1)


class WaterDayOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: dt.date
    ml: int
    target_ml: int


class WaterIn(BaseModel):
    date: dt.date | None = None
    # Отрицательное значение — отмена лишнего
    delta_ml: int = Field(ge=-2000, le=2000)

    @field_validator("delta_ml")
    @classmethod
    def _check_not_zero(cls, value: int) -> int:
        if value == 0:
            raise ValueError("количество воды не может быть нулевым")
        return value
