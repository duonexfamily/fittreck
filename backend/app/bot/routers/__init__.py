from aiogram import Router

from app.bot.routers import start


def build_router() -> Router:
    router = Router()
    router.include_router(start.router)
    return router
