from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, Response, status

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas.body import WaterDayOut, WaterIn, WeightEntryOut, WeightIn
from app.services import water, weight

router = APIRouter(tags=["body"])


@router.get("/weight", response_model=list[WeightEntryOut])
async def get_weight(
    user: CurrentUser,
    session: SessionDep,
    days: Annotated[int, Query(ge=1, le=366)] = weight.HISTORY_DAYS,
) -> list[weight.WeightEntry]:
    return await weight.get_history(session, user, days)


@router.put("/weight", response_model=WeightEntryOut)
async def put_weight(body: WeightIn, user: CurrentUser, session: SessionDep) -> weight.WeightEntry:
    try:
        return await weight.log_weight(session, user, body.date, body.weight_kg)
    except weight.FutureDateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Дата в будущем"
        ) from exc


@router.delete("/weight/{day}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_weight(day: date, user: CurrentUser, session: SessionDep) -> Response:
    try:
        await weight.delete_weight(session, user, day)
    except weight.LastEntryError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT, detail="Нельзя удалить единственную запись"
        ) from exc
    except weight.NotFoundError as exc:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Запись не найдена"
        ) from exc
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/water", response_model=WaterDayOut)
async def get_water(
    user: CurrentUser, session: SessionDep, day: Annotated[date | None, Query(alias="date")] = None
) -> water.WaterDay:
    return await water.get_day(session, user, day)


@router.post("/water", response_model=WaterDayOut)
async def post_water(body: WaterIn, user: CurrentUser, session: SessionDep) -> water.WaterDay:
    return await water.add(session, user, body.date, body.delta_ml)
