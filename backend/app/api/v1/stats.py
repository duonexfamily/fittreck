from dataclasses import asdict

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas.stats import DayStatsOut, StreakOut
from app.services.stats import PERIODS, get_summary
from app.services.streaks import get_streak

router = APIRouter(tags=["stats"])


@router.get("/stats/streaks", response_model=StreakOut)
async def get_streaks(user: CurrentUser, session: SessionDep) -> StreakOut:
    s = await get_streak(session, user)
    return StreakOut(current=s.current, best=s.best, today_done=s.today_done, week=list(s.week))


@router.get("/stats/summary", response_model=list[DayStatsOut])
async def get_stats_summary(
    user: CurrentUser, session: SessionDep, days: int = 30
) -> list[DayStatsOut]:
    # Не Literal[7, 30, 90]: из query приходит строка, и pydantic её с Literal не сравнивает
    if days not in PERIODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Период — одно из значений: {', '.join(map(str, PERIODS))} дней",
        )
    return [DayStatsOut(**asdict(d)) for d in await get_summary(session, user, days)]
