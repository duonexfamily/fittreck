from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import open_app_keyboard
from app.core.config import get_settings
from app.core.security import TelegramUser
from app.services.users import register_user

router = Router(name="start")

DISCLAIMER = (
    "ℹ️ Приложение носит информационный характер и не заменяет консультацию "
    "врача, диетолога или тренера."
)


@router.message(CommandStart())
async def cmd_start(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return

    tg = message.from_user
    await register_user(
        session,
        TelegramUser(
            id=tg.id,
            first_name=tg.first_name,
            last_name=tg.last_name,
            username=tg.username,
            language_code=tg.language_code,
        ),
    )

    text = (
        f"Привет, {tg.first_name}! 👋\n\n"
        "Я помогу следить за тренировками, питанием, сном и самочувствием. "
        "Буду напоминать о важном, а всё удобно заполнять в приложении.\n\n"
        f"{DISCLAIMER}"
    )

    settings = get_settings()
    if settings.webapp_is_https:
        await message.answer(text, reply_markup=open_app_keyboard(settings.webapp_url))
    else:
        await message.answer(f"{text}\n\n⚙️ Mini App ещё не подключён: нужен HTTPS-адрес.")
