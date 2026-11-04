from html import escape

from aiogram import Router
from aiogram.filters import Command
from aiogram.types import CallbackQuery, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.bot.keyboards import (
    ReminderCallback,
    reminder_keyboard,
    reminder_text,
    reminders_list_keyboard,
)
from app.bot.routers.start import answer_with_app
from app.db.models import User
from app.services import reminders
from app.services.users import get_by_telegram_id

router = Router(name="settings")

NEED_PROFILE = "Сначала заполни анкету в приложении — тогда напоминания заработают."


def list_text(user: User) -> str:
    return (
        "🔔 <b>Напоминания</b>\n"
        f"Время — по часовому поясу {escape(user.timezone)}.\n"
        "Нажми на пункт, чтобы включить, выключить или поменять время."
    )


async def onboarded_user(session: AsyncSession, telegram_id: int) -> User | None:
    user = await get_by_telegram_id(session, telegram_id)
    return user if user is not None and user.onboarded_at is not None else None


@router.message(Command("settings"))
async def cmd_settings(message: Message, session: AsyncSession) -> None:
    if message.from_user is None:
        return
    user = await onboarded_user(session, message.from_user.id)
    if user is None:
        await answer_with_app(message, NEED_PROFILE)
        return
    settings = await reminders.get_settings(session, user)
    await message.answer(list_text(user), reply_markup=reminders_list_keyboard(settings))


@router.callback_query(ReminderCallback.filter())
async def on_reminder_button(
    callback: CallbackQuery, callback_data: ReminderCallback, session: AsyncSession
) -> None:
    message = callback.message
    user = await onboarded_user(session, callback.from_user.id)
    if user is None or not isinstance(message, Message):
        await callback.answer(NEED_PROFILE, show_alert=True)
        return

    # Данные кнопки приходят от клиента — проверяем, а не доверяем
    kind = callback_data.kind
    action = callback_data.action
    if action == "list":
        settings = await reminders.get_settings(session, user)
        await message.edit_text(list_text(user), reply_markup=reminders_list_keyboard(settings))
        await callback.answer()
        return
    if kind not in reminders.REMINDERS_BY_KIND:
        await callback.answer()
        return

    if action == "toggle":
        settings = await reminders.toggle(session, user, kind)
    elif action == "shift" and callback_data.minutes in reminders.SHIFT_STEPS:
        settings = await reminders.shift(session, user, kind, callback_data.minutes)
    elif action == "open":
        settings = await reminders.get_settings(session, user)
    else:
        await callback.answer()
        return

    setting = settings[kind]
    await message.edit_text(
        reminder_text(kind, setting), reply_markup=reminder_keyboard(kind, setting)
    )
    await callback.answer()
