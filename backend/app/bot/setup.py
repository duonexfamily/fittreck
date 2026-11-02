from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, MenuButtonWebApp, WebAppInfo
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.middlewares import DbSessionMiddleware
from app.bot.routers import build_router
from app.core.config import Settings

WEBHOOK_PATH = "/telegram/webhook"


def create_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(sessionmaker: async_sessionmaker[AsyncSession]) -> Dispatcher:
    # FSM бота минимальна — хватает памяти процесса (см. TECH_SPEC.md)
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware(sessionmaker))
    dp.include_router(build_router())
    return dp


async def configure_bot(bot: Bot, settings: Settings) -> None:
    """Команды и кнопка меню. Webhook настраивается отдельно в main.py."""
    await bot.set_my_commands([BotCommand(command="start", description="Начать")])
    if settings.webapp_is_https:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Открыть",
                web_app=WebAppInfo(url=settings.webapp_url),
            )
        )
