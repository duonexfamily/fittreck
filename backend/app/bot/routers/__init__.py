from aiogram import Router

from app.bot.routers import fallback, settings, start


def build_router() -> Router:
    router = Router()
    router.include_router(start.router)
    router.include_router(settings.router)
    # Последним — иначе перехватит команды
    router.include_router(fallback.router)
    return router
