from fastapi import APIRouter

from app.api.v1 import body, checkins, me, nutrition, stats, workouts

router = APIRouter(prefix="/api/v1")
router.include_router(me.router)
router.include_router(nutrition.router)
router.include_router(body.router)
router.include_router(workouts.router)
router.include_router(checkins.router)
router.include_router(stats.router)
