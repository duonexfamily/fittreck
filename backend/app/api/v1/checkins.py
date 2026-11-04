from datetime import date
from typing import Annotated

from fastapi import APIRouter, HTTPException, Query, status

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas.checkins import CheckinIn, CheckinOut
from app.db.models import Checkin
from app.services import checkins
from app.services.checkins import CheckinValues, FutureDateError, RangeError, sleep_minutes

router = APIRouter(tags=["checkins"])


def _out(c: Checkin) -> CheckinOut:
    return CheckinOut(
        date=c.date,
        bed_time=c.bed_time,
        wake_time=c.wake_time,
        sleep_minutes=sleep_minutes(c.bed_time, c.wake_time),
        sleep_quality=c.sleep_quality,
        energy=c.energy,
        stress=c.stress,
        mood=c.mood,
        note=c.note,
    )


@router.get("/checkins", response_model=list[CheckinOut])
async def get_checkins(
    user: CurrentUser,
    session: SessionDep,
    date_from: Annotated[date | None, Query(alias="from")] = None,
    date_to: Annotated[date | None, Query(alias="to")] = None,
) -> list[CheckinOut]:
    try:
        found = await checkins.list_checkins(session, user, date_from, date_to)
    except RangeError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Период — от 1 до {checkins.MAX_RANGE_DAYS} дней",
        ) from exc
    return [_out(c) for c in found]


@router.put("/checkins/{day}", response_model=CheckinOut)
async def put_checkin(
    day: date, body: CheckinIn, user: CurrentUser, session: SessionDep
) -> CheckinOut:
    try:
        return _out(
            await checkins.save_checkin(session, user, day, CheckinValues(**body.model_dump()))
        )
    except FutureDateError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Дата в будущем"
        ) from exc
