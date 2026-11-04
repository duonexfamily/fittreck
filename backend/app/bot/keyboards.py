from collections.abc import Mapping

from aiogram.filters.callback_data import CallbackData
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.services.reminders import (
    REMINDER_TYPES,
    REMINDERS_BY_KIND,
    SHIFT_STEPS,
    ReminderSetting,
)


def open_app_keyboard(
    webapp_url: str, path: str = "/", text: str = "📱 Открыть приложение"
) -> InlineKeyboardMarkup:
    """Кнопка, открывающая нужный экран Mini App."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text=text, web_app=WebAppInfo(url=f"{webapp_url}{path}"))]
        ]
    )


class ReminderCallback(CallbackData, prefix="rem"):
    # list — список, open — карточка, toggle — вкл/выкл, shift — сдвиг времени
    action: str
    kind: str = ""
    minutes: int = 0


def _fmt_shift(minutes: int) -> str:
    sign = "+" if minutes > 0 else "−"
    value = abs(minutes)
    return f"{sign}{value // 60} ч" if value % 60 == 0 else f"{sign}{value} мин"


def reminders_list_keyboard(settings: Mapping[str, ReminderSetting]) -> InlineKeyboardMarkup:
    rows = []
    for t in REMINDER_TYPES:
        s = settings[t.kind]
        mark = "✅" if s.on else "▫️"
        rows.append(
            [
                InlineKeyboardButton(
                    text=f"{mark} {t.title} · {s.time:%H:%M}",
                    callback_data=ReminderCallback(action="open", kind=t.kind).pack(),
                )
            ]
        )
    return InlineKeyboardMarkup(inline_keyboard=rows)


def reminder_keyboard(kind: str, setting: ReminderSetting) -> InlineKeyboardMarkup:
    toggle_text = "🔕 Выключить" if setting.on else "🔔 Включить"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=toggle_text,
                    callback_data=ReminderCallback(action="toggle", kind=kind).pack(),
                )
            ],
            [
                InlineKeyboardButton(
                    text=_fmt_shift(step),
                    callback_data=ReminderCallback(action="shift", kind=kind, minutes=step).pack(),
                )
                for step in SHIFT_STEPS
            ],
            [
                InlineKeyboardButton(
                    text="« Все напоминания",
                    callback_data=ReminderCallback(action="list").pack(),
                )
            ],
        ]
    )


def reminder_text(kind: str, setting: ReminderSetting) -> str:
    status = "включено ✅" if setting.on else "выключено"
    return (
        f"<b>{REMINDERS_BY_KIND[kind].title}</b>\n"
        f"Время: <b>{setting.time:%H:%M}</b>, {status}\n\n"
        "Если данные за день уже внесены, бот не напомнит."
    )
