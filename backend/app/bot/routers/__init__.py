from aiogram import Router

from app.bot.routers import fallback, start


def build_router() -> Router:
    router = Router()
    router.include_router(start.router)
    # Последним — иначе перехватит команды
    router.include_router(fallback.router)
    return router
