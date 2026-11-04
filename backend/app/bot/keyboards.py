from collections.abc import Mapping
from datetime import date

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


class CheckinCallback(CallbackData, prefix="chk"):
    # Дата чек-ина ISO, поле из QUICK_FIELDS и оценка 1–5
    day: str
    field: str
    value: int


# Вопрос и подписи оценок 1–5 для каждого шага быстрого чек-ина
CHECKIN_STEPS: dict[str, tuple[str, tuple[str, ...]]] = {
    "sleep_quality": ("Как спалось? 😴", ("😫", "😕", "😐", "🙂", "😴")),
    "energy": ("Сколько сейчас энергии? ⚡", ("🪫", "😩", "😐", "🙂", "⚡")),
    "mood": ("Какое настроение?", ("😞", "😕", "😐", "🙂", "😄")),
}
CHECKIN_LABELS = {"sleep_quality": "сон", "energy": "энергия", "mood": "настроение"}


def _checkin_app_button(webapp_url: str, day: date, text: str) -> InlineKeyboardButton:
    return InlineKeyboardButton(
        text=text, web_app=WebAppInfo(url=f"{webapp_url}/checkin?date={day.isoformat()}")
    )


def checkin_step_keyboard(field: str, day: date, webapp_url: str | None) -> InlineKeyboardMarkup:
    """Оценки 1–5 одной строкой. Без HTTPS-адреса кнопку приложения не показываем."""
    _, faces = CHECKIN_STEPS[field]
    rows = [
        [
            InlineKeyboardButton(
                text=f"{value} {face}",
                callback_data=CheckinCallback(day=day.isoformat(), field=field, value=value).pack(),
            )
            for value, face in enumerate(faces, start=1)
        ]
    ]
    if webapp_url:
        rows.append([_checkin_app_button(webapp_url, day, "📝 Подробнее в приложении")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def checkin_done_keyboard(day: date, webapp_url: str | None) -> InlineKeyboardMarkup | None:
    if not webapp_url:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[[_checkin_app_button(webapp_url, day, "🕒 Добавить время сна")]]
    )


def checkin_done_text(values: Mapping[str, int | None]) -> str:
    parts = [
        f"{CHECKIN_LABELS[field]} {values[field]}/5"
        for field in CHECKIN_STEPS
        if values.get(field) is not None
    ]
    return "Готово, чек-ин записан ✅\n" + " · ".join(parts).capitalize()
