import datetime as dt
from decimal import Decimal

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.services.meals import MealType


class NutrientsOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    kcal: float
    protein: float
    fat: float
    carbs: float


class FoodOut(NutrientsOut):
    """КБЖУ на 100 г. own — продукт добавлен пользователем."""

    id: int
    name: str
    own: bool


class FoodIn(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    kcal: Decimal = Field(ge=0, le=900, decimal_places=1)
    protein: Decimal = Field(ge=0, le=100, decimal_places=1)
    fat: Decimal = Field(ge=0, le=100, decimal_places=1)
    carbs: Decimal = Field(ge=0, le=100, decimal_places=1)

    @model_validator(mode="after")
    def _check_macros(self) -> "FoodIn":
        if not self.name.strip():
            raise ValueError("название не может быть пустым")
        if self.protein + self.fat + self.carbs > 100:
            raise ValueError("белков, жиров и углеводов в сумме больше 100 г на 100 г")
        return self


class MealItemOut(NutrientsOut):
    id: int
    food_id: int | None
    name: str
    grams: float


class MealItemIn(BaseModel):
    # Без даты — сегодня в часовом поясе пользователя
    date: dt.date | None = None
    food_id: int
    grams: Decimal = Field(gt=0, le=5000, decimal_places=1)


class MealItemPatch(BaseModel):
    grams: Decimal = Field(gt=0, le=5000, decimal_places=1)


class MealOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    meal_type: MealType
    items: list[MealItemOut]
    total: NutrientsOut


class DiaryOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    date: dt.date
    meals: list[MealOut]
    total: NutrientsOut
