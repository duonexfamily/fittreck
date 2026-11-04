from dataclasses import asdict

from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas.stats import (
    AchievementOut,
    DayStatsOut,
    InsightsOut,
    RecordOut,
    RecordsOut,
    StreakOut,
)
from app.services.achievements import get_achievements, get_records
from app.services.insights import compute_insights
from app.services.profile import get_targets
from app.services.stats import PERIODS, get_summary
from app.services.streaks import get_streak

router = APIRouter(tags=["stats"])


def _check_period(days: int) -> None:
    # Не Literal: из query приходит строка, и pydantic её с Literal не сравнивает
    if days not in PERIODS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Период — 7, 30 или 90 дней либо 0 (всё время)",
        )


@router.get("/stats/streaks", response_model=StreakOut)
async def get_streaks(user: CurrentUser, session: SessionDep) -> StreakOut:
    s = await get_streak(session, user)
    return StreakOut(current=s.current, best=s.best, today_done=s.today_done, week=list(s.week))


@router.get("/stats/summary", response_model=list[DayStatsOut])
async def get_stats_summary(
    user: CurrentUser, session: SessionDep, days: int = 30
) -> list[DayStatsOut]:
    _check_period(days)
    return [DayStatsOut(**asdict(d)) for d in await get_summary(session, user, days)]


@router.get("/stats/insights", response_model=InsightsOut)
async def get_stats_insights(user: CurrentUser, session: SessionDep, days: int = 30) -> InsightsOut:
    _check_period(days)
    targets = await get_targets(session, user)
    kcal_target = targets.targets.kcal if targets else None
    days_stats = await get_summary(session, user, days)
    return InsightsOut(insights=compute_insights(days_stats, kcal_target))


@router.get("/stats/records", response_model=RecordsOut)
async def get_stats_records(user: CurrentUser, session: SessionDep) -> RecordsOut:
    achievements = await get_achievements(session, user)
    return RecordsOut(
        records=[RecordOut(**asdict(r)) for r in await get_records(session, user)],
        achievements=[
            AchievementOut(
                key=a.key,
                emoji=a.emoji,
                title=a.title,
                progress=a.progress,
                goal=a.goal,
                achieved=a.achieved,
            )
            for a in achievements
        ],
    )
