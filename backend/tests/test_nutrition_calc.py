from datetime import date

import pytest

from app.services.nutrition_calc import age_on, calc_bmr, calc_targets


def test_bmr_male() -> None:
    # 10*80 + 6.25*180 - 5*30 + 5 = 1780
    assert calc_bmr("male", 80, 180, 30) == pytest.approx(1780)


def test_bmr_female() -> None:
    # 10*60 + 6.25*165 - 5*25 - 161 = 1345.25
    assert calc_bmr("female", 60, 165, 25) == pytest.approx(1345.25)


def test_targets_maintain_moderate() -> None:
    t = calc_targets("male", 80, 180, 30, "moderate", "maintain")
    assert t.bmr == 1780
    assert t.tdee == 2759  # 1780 * 1.55
    assert t.kcal == 2759
    assert t.protein_g == 128  # 80 * 1.6
    assert t.fat_g == 77  # 25% от 2759 / 9


def test_macros_sum_close_to_kcal() -> None:
    t = calc_targets("female", 65, 168, 28, "light", "lose")
    total = t.protein_g * 4 + t.fat_g * 9 + t.carbs_g * 4
    assert abs(total - t.kcal) <= 10


def test_lose_has_deficit_gain_has_surplus() -> None:
    args = ("male", 90.0, 185.0, 35, "active")
    maintain = calc_targets(*args, "maintain").kcal  # type: ignore[arg-type]
    assert calc_targets(*args, "lose").kcal < maintain  # type: ignore[arg-type]
    assert calc_targets(*args, "gain").kcal > maintain  # type: ignore[arg-type]


def test_kcal_never_below_minimum() -> None:
    t = calc_targets("female", 40, 150, 70, "sedentary", "lose")
    assert t.kcal == 1200


@pytest.mark.parametrize(
    ("birth", "today", "age"),
    [
        (date(2000, 5, 10), date(2026, 5, 9), 25),
        (date(2000, 5, 10), date(2026, 5, 10), 26),
        (date(2000, 2, 29), date(2026, 2, 28), 25),
    ],
)
def test_age_on(birth: date, today: date, age: int) -> None:
    assert age_on(birth, today) == age
