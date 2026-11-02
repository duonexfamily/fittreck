from fastapi import APIRouter

from app.api.deps import CurrentUser
from app.api.schemas.me import MeOut
from app.db.models import User

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeOut)
async def get_me(user: CurrentUser) -> User:
    return user
