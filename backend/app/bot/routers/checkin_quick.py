"""Быстрый чек-ин кнопками в чате: сон, энергия, настроение по шкале 1–5."""

from datetime import date

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    CHECKIN_STEPS,
    CheckinCallback,
    checkin_done_keyboard,
    checkin_done_text,
    checkin_step_keyboard,
)
from app.bot.routers.settings import NEED_PROFILE, onboarded_user
from app.bot.routers.start import answer_with_app
from app.core.config import get_settings
from app.services import checkins, streaks
from app.services.profile import user_today

router = Router(name="checkin_quick")

FIRST_FIELD = checkins.QUICK_FIELDS[0]


def _webapp_url() -> str | None:
    settings = get_settings()
    return settings.webapp_url if settings.webapp_is_https else None


def next_field(field: str) -> str | None:
    """Следующий вопрос или None, если этот был последним."""
    index = checkins.QUICK_FIELDS.index(field) + 1
    return checkins.QUICK_FIELDS[index] if index < len(checkins.QUICK_FIELDS) else None


@router.message(Command("checkin"))
async def cmd_checkin(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await onboarded_user(session, message.from_user.id)
    if user is None:
        await answer_with_app(message, NEED_PROFILE)
        return
    question, _ = CHECKIN_STEPS[FIRST_FIELD]
    keyboard = checkin_step_keyboard(FIRST_FIELD, user_today(user), _webapp_url())
    await message.answer(question, reply_markup=keyboard)


@router.callback_query(CheckinCallback.filter())
async def on_checkin_button(
    callback: CallbackQuery, callback_data: CheckinCallback, session: AsyncSession
) -> None:
    message = callback.message
    user = await onboarded_user(session, callback.from_user.id)
    if user is None or not isinstance(message, Message):
        await callback.answer(NEED_PROFILE, show_alert=True)
        return

    # Данные кнопки приходят от клиента — проверяем, а не доверяем
    try:
        day = date.fromisoformat(callback_data.day)
        checkin = await checkins.save_quick(
            session, user, day, callback_data.field, callback_data.value
        )
    except (ValueError, checkins.FutureDateError):
        await callback.answer()
        return

    webapp_url = _webapp_url()
    following = next_field(callback_data.field)
    if following is None:
        values = {field: getattr(checkin, field) for field in CHECKIN_STEPS}
        streak = await streaks.get_streak(session, user)
        await message.edit_text(
            checkin_done_text(values, streak.current),
            reply_markup=checkin_done_keyboard(
                day, webapp_url, has_sleep_time=checkin.bed_time is not None
            ),
        )
    else:
        question, _ = CHECKIN_STEPS[following]
        await message.edit_text(
            question, reply_markup=checkin_step_keyboard(following, day, webapp_url)
        )
    await callback.answer("Записал ✅")
