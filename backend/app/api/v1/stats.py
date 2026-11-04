from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Query

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas.stats import DayStatsOut, StreakOut
from app.services.stats import get_summary
from app.services.streaks import get_streak

router = APIRouter(tags=["stats"])


@router.get("/stats/streaks", response_model=StreakOut)
async def get_streaks(user: CurrentUser, session: SessionDep) -> StreakOut:
    s = await get_streak(session, user)
    return StreakOut(current=s.current, best=s.best, today_done=s.today_done, week=list(s.week))


@router.get("/stats/summary", response_model=list[DayStatsOut])
async def get_stats_summary(
    user: CurrentUser,
    session: SessionDep,
    days: Annotated[Literal[7, 30, 90], Query()] = 30,
) -> list[DayStatsOut]:
    return [DayStatsOut(**asdict(d)) for d in await get_summary(session, user, days)]
