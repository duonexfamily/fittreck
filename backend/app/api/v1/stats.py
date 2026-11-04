from fastapi import APIRouter

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas.stats import StreakOut
from app.services.streaks import get_streak

router = APIRouter(tags=["stats"])


@router.get("/stats/streaks", response_model=StreakOut)
async def get_streaks(user: CurrentUser, session: SessionDep) -> StreakOut:
    s = await get_streak(session, user)
    return StreakOut(current=s.current, best=s.best, today_done=s.today_done, week=list(s.week))
