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
    QuickItemIn,
    QuickNutrientsIn,
)
from app.db.models import Food, MealItem
from app.services import meals
from app.services.meals import MealType, NotFoundError, Nutrients, WrongItemKindError

router = APIRouter(tags=["nutrition"])


def _food_out(food: Food, favorites: set[int]) -> FoodOut:
    # Чужие продукты не видны, поэтому любой продукт с владельцем — свой
    return FoodOut(
        id=food.id,
        name=food.name,
        kcal=float(food.kcal),
        protein=float(food.protein),
        fat=float(food.fat),
        carbs=float(food.carbs),
        own=food.owner_id is not None,
        favorite=food.id in favorites,
    )


def _nutrients(body: QuickNutrientsIn) -> Nutrients:
    return Nutrients(kcal=body.kcal, protein=body.protein, fat=body.fat, carbs=body.carbs)


def _not_found(detail: str) -> HTTPException:
    return HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)


@router.get("/foods", response_model=list[FoodOut])
async def get_foods(
    user: CurrentUser,
    session: SessionDep,
    query: Annotated[str, Query(max_length=64)] = "",
) -> list[FoodOut]:
    foods = await meals.search_foods(session, user, query)
    favorites = await meals.favorite_ids(session, user, foods)
    return [_food_out(f, favorites) for f in foods]


@router.get("/foods/favorites", response_model=list[FoodOut])
async def get_favorite_foods(user: CurrentUser, session: SessionDep) -> list[FoodOut]:
    foods = await meals.list_favorites(session, user)
    return [_food_out(f, {f.id for f in foods}) for f in foods]


@router.put("/foods/{food_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def put_favorite(food_id: int, user: CurrentUser, session: SessionDep) -> Response:
    try:
        await meals.set_favorite(session, user, food_id, favorite=True)
    except NotFoundError as exc:
        raise _not_found("Продукт не найден") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/foods/{food_id}/favorite", status_code=status.HTTP_204_NO_CONTENT)
async def delete_favorite(food_id: int, user: CurrentUser, session: SessionDep) -> Response:
    try:
        await meals.set_favorite(session, user, food_id, favorite=False)
    except NotFoundError as exc:
        raise _not_found("Продукт не найден") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/foods", response_model=FoodOut, status_code=status.HTTP_201_CREATED)
async def post_food(body: FoodIn, user: CurrentUser, session: SessionDep) -> FoodOut:
    per_100g = Nutrients(kcal=body.kcal, protein=body.protein, fat=body.fat, carbs=body.carbs)
    return _food_out(await meals.create_food(session, user, body.name, per_100g), set())


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


@router.post(
    "/meals/{meal_type}/quick-items",
    response_model=MealItemOut,
    status_code=status.HTTP_201_CREATED,
)
async def post_quick_item(
    meal_type: MealType, body: QuickItemIn, user: CurrentUser, session: SessionDep
) -> MealItem:
    return await meals.add_quick_item(
        session, user, body.date, meal_type, body.name, _nutrients(body)
    )


@router.patch("/meal-items/{item_id}", response_model=MealItemOut)
async def patch_meal_item(
    item_id: int, body: MealItemPatch, user: CurrentUser, session: SessionDep
) -> MealItem:
    try:
        # Валидатор схемы гарантирует, что задано ровно одно из полей
        if body.grams is not None:
            return await meals.update_item_grams(session, user, item_id, body.grams)
        if body.quick is not None:
            return await meals.update_quick_item(
                session, user, item_id, body.quick.name, _nutrients(body.quick)
            )
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY)
    except NotFoundError as exc:
        raise _not_found("Запись не найдена") from exc
    except WrongItemKindError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="У быстрой записи меняются КБЖУ, у продукта — граммовка",
        ) from exc


@router.delete("/meal-items/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_meal_item(item_id: int, user: CurrentUser, session: SessionDep) -> Response:
    try:
        await meals.delete_item(session, user, item_id)
    except NotFoundError as exc:
        raise _not_found("Запись не найдена") from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)
