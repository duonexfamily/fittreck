import importlib.util
from decimal import Decimal
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from pydantic import ValidationError

from app.api.schemas.nutrition import FoodIn, MealItemIn, MealItemPatch, QuickItemIn
from app.main import app
from app.services.meals import ZERO, Nutrients, portion, scale, total

client = TestClient(app)

CHICKEN = Nutrients(Decimal("113"), Decimal("23.6"), Decimal("1.9"), Decimal("0.4"))


def test_portion_150g() -> None:
    n = portion(CHICKEN, Decimal("150"))
    assert n == Nutrients(Decimal("169.50"), Decimal("35.40"), Decimal("2.85"), Decimal("0.60"))


def test_portion_rounds_half_up() -> None:
    n = portion(Nutrients(Decimal("1.5"), Decimal(0), Decimal(0), Decimal(0)), Decimal("1"))
    assert n.kcal == Decimal("0.02")  # 0.015 → 0.02


def test_scale_changes_grams_proportionally() -> None:
    item = portion(CHICKEN, Decimal("100"))
    doubled = scale(item, Decimal("200") / Decimal("100"))
    assert doubled == portion(CHICKEN, Decimal("200"))


def test_total() -> None:
    a = Nutrients(Decimal("100"), Decimal("10"), Decimal("5"), Decimal("1"))
    b = Nutrients(Decimal("50.5"), Decimal("1"), Decimal("1"), Decimal("10"))
    assert total([a, b]) == Nutrients(Decimal("150.5"), Decimal("11"), Decimal("6"), Decimal("11"))
    assert total([]) == ZERO


def test_food_in_rejects_macros_over_100g() -> None:
    with pytest.raises(ValidationError):
        FoodIn(
            name="Ошибка",
            kcal=Decimal(500),
            protein=Decimal(50),
            fat=Decimal(40),
            carbs=Decimal(20),
        )


def test_food_in_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        FoodIn(name="   ", kcal=Decimal(1), protein=Decimal(0), fat=Decimal(0), carbs=Decimal(0))


@pytest.mark.parametrize("grams", ["0", "-5", "5001", "10.25"])
def test_meal_item_in_rejects_bad_grams(grams: str) -> None:
    with pytest.raises(ValidationError):
        MealItemIn(food_id=1, grams=Decimal(grams))


def test_quick_item_default_name() -> None:
    item = QuickItemIn(kcal=Decimal(520), protein=Decimal(30), fat=Decimal(20), carbs=Decimal(50))
    assert item.name == "Быстрая запись"
    assert item.date is None


def test_quick_item_rejects_all_zero() -> None:
    with pytest.raises(ValidationError):
        QuickItemIn(kcal=Decimal(0), protein=Decimal(0), fat=Decimal(0), carbs=Decimal(0))


def test_quick_item_rejects_blank_name() -> None:
    with pytest.raises(ValidationError):
        QuickItemIn(name="  ", kcal=Decimal(100), protein=0, fat=0, carbs=0)


def test_meal_item_patch_needs_exactly_one_field() -> None:
    quick = {"kcal": 100, "protein": 0, "fat": 0, "carbs": 0}
    assert MealItemPatch.model_validate({"grams": 150}).grams == Decimal(150)
    assert MealItemPatch.model_validate({"quick": quick}).quick is not None
    with pytest.raises(ValidationError):
        MealItemPatch.model_validate({})
    with pytest.raises(ValidationError):
        MealItemPatch.model_validate({"grams": 150, "quick": quick})


@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("get", "/api/v1/foods?query=рис"),
        ("post", "/api/v1/foods"),
        ("get", "/api/v1/meals"),
        ("post", "/api/v1/meals/lunch/items"),
        ("post", "/api/v1/meals/lunch/quick-items"),
        ("get", "/api/v1/foods/favorites"),
        ("put", "/api/v1/foods/1/favorite"),
        ("delete", "/api/v1/foods/1/favorite"),
        ("patch", "/api/v1/meal-items/1"),
        ("delete", "/api/v1/meal-items/1"),
    ],
)
def test_nutrition_endpoints_require_auth(method: str, path: str) -> None:
    assert client.request(method, path).status_code == 401


def _load_seed() -> list[tuple[str, float, float, float, float]]:
    path = next(Path(__file__).parent.parent.glob("migrations/versions/*_0004_seed_foods.py"))
    spec = importlib.util.spec_from_file_location("seed_foods", path)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module.FOODS  # type: ignore[no-any-return]


def test_seed_foods_are_consistent() -> None:
    foods = _load_seed()
    names = [f[0] for f in foods]
    assert len(names) == len(set(names)), "повторяющиеся названия"
    for name, kcal, p, f, c in foods:
        assert p + f + c <= 100, name
        # Калории по Этуотеру (4/9/4) расходятся с табличными не больше чем на 15%
        atwater = p * 4 + f * 9 + c * 4
        assert abs(atwater - kcal) <= max(0.15 * kcal, 5), name
