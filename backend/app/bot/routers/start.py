from html import escape

from aiogram import Router
from aiogram.filters import Command, CommandStart
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

HELP_TEXT = (
    "Всё главное — в приложении: анкета и норма калорий, дневник питания, вода и вес.\n"
    "Я напоминаю записать еду и выпить воды. Скоро появятся тренировки и сон.\n\n"
    "Команды:\n"
    "/start — начать и открыть приложение\n"
    "/settings — напоминания: время, вкл/выкл\n"
    "/help — эта подсказка"
)


async def answer_with_app(message: Message, text: str) -> None:
    """Ответ с кнопкой Mini App. Без HTTPS-адреса кнопку не показываем."""
    settings = get_settings()
    if settings.webapp_is_https:
        await message.answer(text, reply_markup=open_app_keyboard(settings.webapp_url))
    else:
        await message.answer(f"{text}\n\n⚙️ Mini App ещё не подключён: нужен HTTPS-адрес.")


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

    # Режим разметки HTML: имя с «<» или «&» без экранирования ломает сообщение
    text = (
        f"Привет, {escape(tg.first_name)}! 👋\n\n"
        "Я помогу следить за тренировками, питанием, сном и самочувствием. "
        "Буду напоминать о важном, а всё удобно заполнять в приложении.\n\n"
        f"{DISCLAIMER}"
    )
    await answer_with_app(message, text)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await answer_with_app(message, HELP_TEXT)
