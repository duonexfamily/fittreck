from aiogram import F, Router
from aiogram.enums import ChatType
from aiogram.types import Message

from app.bot.routers.start import answer_with_app

# Подключается последним: ловит всё, что не разобрали другие роутеры.
# Только личные чаты — в группе бот не должен отвечать на каждое сообщение
router = Router(name="fallback")
router.message.filter(F.chat.type == ChatType.PRIVATE)


@router.message()
async def any_message(message: Message) -> None:
    # Без ответа бот выглядит сломанным — подсказываем, где всё находится
    await answer_with_app(
        message,
        "Я пока не понимаю сообщения. Всё заполняется в приложении — кнопка ниже. "
        "Список команд: /help",
    )
