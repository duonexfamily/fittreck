from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def open_app_keyboard(webapp_url: str, path: str = "/") -> InlineKeyboardMarkup:
    """Кнопка, открывающая нужный экран Mini App."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="📱 Открыть приложение",
                    web_app=WebAppInfo(url=f"{webapp_url}{path}"),
                )
            ]
        ]
    )
