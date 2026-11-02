import asyncio
import contextlib
import hmac
import logging
import os
from collections.abc import AsyncIterator
from pathlib import Path
from typing import Annotated, Any

import uvicorn
from aiogram.types import Update
from fastapi import FastAPI, Header, HTTPException, Request, Response, status
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.v1 import router as api_router
from app.bot.setup import WEBHOOK_PATH, configure_bot, create_bot, create_dispatcher
from app.core.config import get_settings
from app.core.keepalive import keepalive_loop
from app.core.logging import setup_logging
from app.db.session import create_engine, create_sessionmaker

logger = logging.getLogger(__name__)

# Собранный Mini App (webapp/dist) кладётся сюда при сборке Docker-образа
STATIC_DIR = (Path(__file__).resolve().parent.parent / "static").resolve()


@contextlib.asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    settings = get_settings()
    setup_logging(settings.log_level)

    engine = create_engine(settings)
    sessionmaker = create_sessionmaker(engine)
    bot = create_bot(settings)
    dp = create_dispatcher(sessionmaker)

    app.state.sessionmaker = sessionmaker
    app.state.bot = bot
    app.state.dp = dp

    await configure_bot(bot, settings)

    polling_task: asyncio.Task[Any] | None = None
    if settings.env == "prod":
        if settings.webhook_token is None:  # уже проверено в Settings, здесь для mypy
            raise RuntimeError("WEBHOOK_SECRET не задан")
        await bot.set_webhook(
            url=f"{settings.webapp_url}{WEBHOOK_PATH}",
            secret_token=settings.webhook_token,
            allowed_updates=dp.resolve_used_update_types(),
        )
        logger.info("Webhook установлен")
    else:
        await bot.delete_webhook()
        polling_task = asyncio.create_task(dp.start_polling(bot, handle_signals=False))
        logger.info("Бот запущен в режиме polling")

    keepalive_task: asyncio.Task[None] | None = None
    if settings.keepalive_minutes and settings.webapp_is_https:
        keepalive_task = asyncio.create_task(
            keepalive_loop(settings.webapp_url, sessionmaker, settings.keepalive_minutes)
        )
        logger.info("Самопинг включён: раз в %s мин", settings.keepalive_minutes)

    try:
        yield
    finally:
        if keepalive_task is not None:
            keepalive_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await keepalive_task
        if polling_task is not None:
            await dp.stop_polling()
            polling_task.cancel()
            with contextlib.suppress(asyncio.CancelledError):
                await polling_task
        await bot.session.close()
        await engine.dispose()


app = FastAPI(title="FitTrack API", lifespan=lifespan, docs_url=None, redoc_url=None)
app.include_router(api_router)


@app.get("/health", include_in_schema=False)
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post(WEBHOOK_PATH, include_in_schema=False)
async def telegram_webhook(
    request: Request,
    x_telegram_bot_api_secret_token: Annotated[str | None, Header()] = None,
) -> Response:
    token = get_settings().webhook_token
    if (
        token is None
        or x_telegram_bot_api_secret_token is None
        or not hmac.compare_digest(x_telegram_bot_api_secret_token, token)
    ):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN)

    bot = request.app.state.bot
    update = Update.model_validate(await request.json(), context={"bot": bot})
    await request.app.state.dp.feed_update(bot, update)
    return Response(status_code=status.HTTP_200_OK)


if (STATIC_DIR / "index.html").is_file():
    if (STATIC_DIR / "assets").is_dir():
        app.mount("/assets", StaticFiles(directory=STATIC_DIR / "assets"), name="assets")

    @app.get("/{full_path:path}", include_in_schema=False)
    async def spa(full_path: str) -> FileResponse:
        """Статика Mini App. Неизвестные пути отдают index.html (маршруты react-router)."""
        if full_path.startswith("api/"):
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND)
        candidate = (STATIC_DIR / full_path).resolve()
        if full_path and candidate.is_file() and candidate.is_relative_to(STATIC_DIR):
            return FileResponse(candidate)
        return FileResponse(STATIC_DIR / "index.html")


if __name__ == "__main__":
    uvicorn.run(
        "app.main:app",
        # Локально — только localhost. В Docker HOST=0.0.0.0 задан в Dockerfile
        host=os.getenv("HOST", "127.0.0.1"),
        port=int(os.getenv("PORT", "8000")),
        proxy_headers=True,
    )
