from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas.nutrition import (
    DiaryOut,
    FoodIn,
    FoodOut,
    MealItemIn,
    MealItemOut,
    MealItemPatch,
)
from app.db.models import Food, MealItem
from app.services import meals
from app.services.meals import MealType, NotFoundError, Nutrients

router = APIRouter(tags=["nutrition"])


def _food_out(food: Food) -> FoodOut:
    # Чужие продукты не видны, поэтому любой продукт с владельцем — свой
    return FoodOut(
        id=food.id,
        name=food.name,
        kcal=float(food.kcal),
        protein=float(food.protein),
        fat=float(food.fat),
        carbs=float(food.carbs),
        own=food.owner_id is not None,
    )


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


@router.get("/foods", response_model=list[FoodOut])
async def get_foods(
    user: CurrentUser,
    session: SessionDep,
    query: Annotated[str, Query(max_length=64)] = "",
) -> list[FoodOut]:
    return [_food_out(f) for f in await meals.search_foods(session, user, query)]


@router.post("/foods", response_model=FoodOut, status_code=status.HTTP_201_CREATED)
async def post_food(body: FoodIn, user: CurrentUser, session: SessionDep) -> FoodOut:
    per_100g = Nutrients(kcal=body.kcal, protein=body.protein, fat=body.fat, carbs=body.carbs)
    return _food_out(await meals.create_food(session, user, body.name, per_100g))


@router.get("/meals", response_model=DiaryOut)
async def get_meals(
    user: CurrentUser, session: SessionDep, day: Annotated[date | None, Query(alias="date")] = None
) -> meals.Diary:
    return await meals.get_diary(session, user, day)


@router.post(
    "/meals/{meal_type}/items", response_model=MealItemOut, status_code=status.HTTP_201_CREATED
)
async def post_meal_item(
    meal_type: MealType, body: MealItemIn, user: CurrentUser, session: SessionDep
) -> MealItem:
    try:
        return await meals.add_item(session, user, body.date, meal_type, body.food_id, body.grams)
    except NotFoundError as exc:
        raise _not_found("Продукт не найден") from exc


@router.patch("/meal-items/{item_id}", response_model=MealItemOut)
async def patch_meal_item(
    item_id: int, body: MealItemPatch, user: CurrentUser, session: SessionDep
) -> MealItem:
    try:
        return await meals.update_item_grams(session, user, item_id, body.grams)
    except NotFoundError as exc:
        raise _not_found("Запись не найдена") from exc


@router.delete("/meal-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_item(item_id: int, user: CurrentUser, session: SessionDep) -> Response:
    try:
        await meals.delete_item(session, user, item_id)
    except NotFoundError as exc:
        raise _not_found("Запись не найдена") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
