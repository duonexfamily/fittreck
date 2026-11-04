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
    favorite: bool = False


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
    """grams = None — быстрая запись без продукта."""

    id: int
    food_id: int | None
    name: str
    grams: float | None


class MealItemIn(BaseModel):
    # Без даты — сегодня в часовом поясе пользователя
    date: dt.date | None = None
    food_id: int
    grams: Decimal = Field(gt=0, le=5000, decimal_places=1)


class QuickNutrientsIn(BaseModel):
    """КБЖУ порции целиком, введённые вручную."""

    name: str = Field(default="Быстрая запись", min_length=1, max_length=128)
    kcal: Decimal = Field(ge=0, le=5000, decimal_places=1)
    protein: Decimal = Field(ge=0, le=500, decimal_places=1)
    fat: Decimal = Field(ge=0, le=500, decimal_places=1)
    carbs: Decimal = Field(ge=0, le=500, decimal_places=1)

    @model_validator(mode="after")
    def _check(self) -> "QuickNutrientsIn":
        if not self.name.strip():
            raise ValueError("название не может быть пустым")
        if self.kcal + self.protein + self.fat + self.carbs == 0:
            raise ValueError("укажите калории или БЖУ")
        return self


class QuickItemIn(QuickNutrientsIn):
    # Без даты — сегодня в часовом поясе пользователя
    date: dt.date | None = None


class MealItemPatch(BaseModel):
    """У продукта меняется граммовка, у быстрой записи — название и КБЖУ."""

    grams: Decimal | None = Field(default=None, gt=0, le=5000, decimal_places=1)
    quick: QuickNutrientsIn | None = None

    @model_validator(mode="after")
    def _one_of(self) -> "MealItemPatch":
        if (self.grams is None) == (self.quick is None):
            raise ValueError("передайте grams или quick")
        return self


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
