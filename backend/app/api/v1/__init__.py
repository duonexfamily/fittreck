from fastapi import APIRouter

from app.api.v1 import body, me, nutrition, workouts

router = APIRouter(prefix="/api/v1")
router.include_router(me.router)
router.include_router(nutrition.router)
router.include_router(body.router)
router.include_router(workouts.router)
