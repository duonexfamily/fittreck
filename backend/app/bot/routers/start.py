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

# Общий блок команд для приветствия и /help — один источник, чтобы списки не расходились
COMMANDS_TEXT = (
    "<b>⌨️ Команды</b>\n"
    "/checkin — чек-ин за 10 секунд: сон, энергия, настроение\n"
    "/settings — напоминания: время, вкл/выкл\n"
    "/help — что я умею\n"
    "/start — открыть приложение заново\n"
    "/delete_me — удалить все свои данные"
)

FEATURES_TEXT = (
    "🏋️ <b>Тренировки</b> — план, подходы, RPE и личные рекорды\n"
    "🍽 <b>Питание</b> — КБЖУ, вода и вес под твою норму\n"
    "😴 <b>Сон и самочувствие</b> — короткий чек-ин каждое утро\n"
    "🔥 <b>Серии и достижения</b> — графики, итоги недели, награды"
)

HELP_TEXT = (
    "<b>Что я умею</b>\n\n"
    f"{FEATURES_TEXT}\n\n"
    "⏰ Напоминаю о еде, воде и тренировках по плану, утром спрошу, как спалось, "
    "а вечером пришлю итог дня.\n\n"
    f"{COMMANDS_TEXT}"
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
        f"<b>Привет, {escape(tg.first_name)}!</b> 👋\n"
        "Я — <b>FitTrack</b>, твой карманный тренер по здоровью. "
        "Бесплатно, без рекламы и подписок.\n\n"
        f"{FEATURES_TEXT}\n\n"
        f"{COMMANDS_TEXT}\n\n"
        "Жми <b>«Открыть приложение»</b> — первая запись запустит твою серию 🔥\n\n"
        f"<blockquote>{DISCLAIMER}</blockquote>"
    )
    await answer_with_app(message, text)


@router.message(Command("help"))
async def cmd_help(message: Message) -> None:
    await answer_with_app(message, HELP_TEXT)
