"""Расчёт нормы калорий и БЖУ.

Базовый обмен — формула Миффлина — Сан Жеора, умноженная на коэффициент активности.
Результат информационный, не медицинская рекомендация.
"""

from dataclasses import dataclass
from datetime import date
from typing import Literal

Sex = Literal["male", "female"]
Goal = Literal["lose", "maintain", "gain"]
Activity = Literal["sedentary", "light", "moderate", "active", "very_active"]

ACTIVITY_FACTORS: dict[Activity, float] = {
    "sedentary": 1.2,
    "light": 1.375,
    "moderate": 1.55,
    "active": 1.725,
    "very_active": 1.9,
}

# Дефицит 15% для похудения, профицит 10% для набора
GOAL_KCAL_FACTORS: dict[Goal, float] = {"lose": 0.85, "maintain": 1.0, "gain": 1.10}

# Белок в граммах на кг веса тела
PROTEIN_G_PER_KG: dict[Goal, float] = {"lose": 2.0, "maintain": 1.6, "gain": 1.8}

# Доля калорий из жиров
FAT_SHARE = 0.25

# Нижняя граница калорий — ниже без контроля специалиста не опускаемся
MIN_KCAL: dict[Sex, int] = {"male": 1500, "female": 1200}

KCAL_PER_G_PROTEIN = 4
KCAL_PER_G_CARBS = 4
KCAL_PER_G_FAT = 9


@dataclass(frozen=True, slots=True)
class Targets:
    bmr: int
    tdee: int
    kcal: int
    protein_g: int
    fat_g: int
    carbs_g: int


def age_on(birth_date: date, today: date) -> int:
    """Полных лет на дату."""
    had_birthday = (today.month, today.day) >= (birth_date.month, birth_date.day)
    return today.year - birth_date.year - (0 if had_birthday else 1)


def calc_bmr(sex: Sex, weight_kg: float, height_cm: float, age: int) -> float:
    """Базовый обмен веществ, ккал/сутки (Миффлин — Сан Жеор)."""
    base = 10 * weight_kg + 6.25 * height_cm - 5 * age
    return base + 5 if sex == "male" else base - 161


def calc_targets(
    sex: Sex,
    weight_kg: float,
    height_cm: float,
    age: int,
    activity: Activity,
    goal: Goal,
) -> Targets:
    bmr = calc_bmr(sex, weight_kg, height_cm, age)
    tdee = bmr * ACTIVITY_FACTORS[activity]
    kcal = max(round(tdee * GOAL_KCAL_FACTORS[goal]), MIN_KCAL[sex])

    protein_g = round(weight_kg * PROTEIN_G_PER_KG[goal])
    fat_g = round(kcal * FAT_SHARE / KCAL_PER_G_FAT)
    carbs_kcal = kcal - protein_g * KCAL_PER_G_PROTEIN - fat_g * KCAL_PER_G_FAT
    carbs_g = max(round(carbs_kcal / KCAL_PER_G_CARBS), 0)

    return Targets(
        bmr=round(bmr),
        tdee=round(tdee),
        kcal=kcal,
        protein_g=protein_g,
        fat_g=fat_g,
        carbs_g=carbs_g,
    )
