"""Удаление всех данных пользователя — с подтверждением кнопкой."""

from aiogram import Router
from aiogram.filters import Command
from aiogram.filters.callback_data import CallbackData
from aiogram.types import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.users import delete_user, get_by_telegram_id

router = Router(name="account")

CONFIRM_TEXT = (
    "⚠️ <b>Удалить все данные?</b>\n"
    "Сотрутся анкета, дневник питания, вода, вес, тренировки, чек-ины и настройки напоминаний.\n"
    "Восстановить их будет нельзя."
)
DELETED_TEXT = "Все данные удалены. Если захочешь начать заново — отправь /start."
CANCELLED_TEXT = "Хорошо, ничего не удаляю 👍"


class DeleteCallback(CallbackData, prefix="del"):
    # confirm — удалить, cancel — передумал
    action: str


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="🗑 Да, удалить всё",
                    callback_data=DeleteCallback(action="confirm").pack(),
                ),
                InlineKeyboardButton(
                    text="Отмена", callback_data=DeleteCallback(action="cancel").pack()
                ),
            ]
        ]
    )


@router.message(Command("delete_me"))
async def cmd_delete_me(message: Message) -> None:
    await message.answer(CONFIRM_TEXT, reply_markup=confirm_keyboard())


@router.callback_query(DeleteCallback.filter())
async def on_delete_button(
    callback: CallbackQuery, callback_data: DeleteCallback, session: AsyncSession
) -> None:
    message = callback.message
    if not isinstance(message, Message):
        await callback.answer()
        return
    if callback_data.action != "confirm":
        await message.edit_text(CANCELLED_TEXT)
        await callback.answer()
        return

    # Пользователь — только тот, кто нажал кнопку, а не тот, кому отправлено сообщение
    user = await get_by_telegram_id(session, callback.from_user.id)
    if user is not None:
        await delete_user(session, user)
    await message.edit_text(DELETED_TEXT)
    await callback.answer()
