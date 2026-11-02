from fastapi import APIRouter, HTTPException, status

from app.api.deps import CurrentUser, SessionDep
from app.api.schemas.me import MeOut, ProfileIn, TargetsOut
from app.db.models import User
from app.services.profile import ProfileData, get_targets, save_profile

router = APIRouter(tags=["me"])


@router.get("/me", response_model=MeOut)
async def get_me(user: CurrentUser) -> User:
    return user


@router.put("/me/profile", response_model=MeOut)
async def put_profile(body: ProfileIn, user: CurrentUser, session: SessionDep) -> User:
    await save_profile(session, user, ProfileData(**body.model_dump()))
    return user


@router.get("/me/targets", response_model=TargetsOut)
async def get_me_targets(user: CurrentUser, session: SessionDep) -> TargetsOut:
    result = await get_targets(session, user)
    if result is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Анкета не заполнена")
    t = result.targets
    return TargetsOut(
        weight_kg=result.weight_kg,
        bmr=t.bmr,
        tdee=t.tdee,
        kcal=t.kcal,
        protein_g=t.protein_g,
        fat_g=t.fat_g,
        carbs_g=t.carbs_g,
    )
