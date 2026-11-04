import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, ErrorEvent, MenuButtonWebApp, WebAppInfo
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from app.bot.middlewares import DbSessionMiddleware
from app.bot.routers import build_router
from app.core.config import Settings

logger = logging.getLogger(__name__)

WEBHOOK_PATH = "/telegram/webhook"


def create_bot(settings: Settings) -> Bot:
    return Bot(
        token=settings.bot_token.get_secret_value(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


async def on_error(event: ErrorEvent) -> bool:
    """Логирует ошибку и гасит её.

    Иначе webhook ответит 500, Telegram будет повторять тот же апдейт,
    и бот перестанет отвечать на новые сообщения.
    """
    logger.error("Ошибка при обработке апдейта", exc_info=event.exception)
    return True


def create_dispatcher(sessionmaker: async_sessionmaker[AsyncSession]) -> Dispatcher:
    # FSM бота минимальна — хватает памяти процесса (см. TECH_SPEC.md)
    dp = Dispatcher(storage=MemoryStorage())
    dp.update.middleware(DbSessionMiddleware(sessionmaker))
    dp.errors.register(on_error)
    dp.include_router(build_router())
    return dp


async def configure_bot(bot: Bot, settings: Settings) -> None:
    """Команды и кнопка меню. Webhook настраивается отдельно в main.py."""
    await bot.set_my_commands(
        [
            BotCommand(command="start", description="Начать"),
            BotCommand(command="settings", description="Напоминания"),
            BotCommand(command="help", description="Что умеет бот"),
        ]
    )
    if settings.webapp_is_https:
        await bot.set_chat_menu_button(
            menu_button=MenuButtonWebApp(
                text="Открыть",
                web_app=WebAppInfo(url=settings.webapp_url),
            )
        )
