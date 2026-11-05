"""Напоминания: настройки пользователя и выбор, кому и что отправить."""

from collections.abc import Iterator, Mapping, Sequence
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from sqlalchemy.ext.asyncio import AsyncSession

from app.db.models import User
from app.db.repositories.checkins import CheckinRepository
from app.db.repositories.meals import MealRepository
from app.db.repositories.reminders import ReminderRepository
from app.db.repositories.stats import StatsRepository
from app.db.repositories.workouts import WorkoutRepository
from app.services import streaks, water
from app.services.profile import get_targets
from app.services.stats import DayStats, get_summary


@dataclass(frozen=True, slots=True)
class ReminderType:
    kind: str
    title: str
    default_time: time
    default_on: bool
    text: str
    # Пустая подпись — сообщение без кнопки
    button: str
    # Экран Mini App, который открывает кнопка
    path: str
    # День недели (0 — понедельник). None — каждый день
    weekday: int | None = None


REMINDER_TYPES: tuple[ReminderType, ...] = (
    ReminderType(
        "breakfast", "🍳 Завтрак", time(9, 30), False,
        "Запиши завтрак — это займёт пару секунд 🍳", "🍳 Записать", "/nutrition?meal=breakfast",
    ),
    ReminderType(
        "workout", "🏋️ Тренировка", time(10, 0), True,
        "Сегодня тренировка по плану 🏋️ Удачи!", "🏋️ Открыть тренировку", "/workouts",
    ),
    ReminderType(
        "lunch", "🍲 Обед", time(13, 30), True,
        "Запиши обед за 5 секунд 🍲", "🍲 Записать", "/nutrition?meal=lunch",
    ),
    ReminderType(
        "water", "💧 Вода", time(16, 0), True,
        "Не забывай про воду 💧 Отметь, сколько уже выпито.", "💧 Отметить", "/nutrition",
    ),
    ReminderType(
        "dinner", "🍽 Ужин", time(19, 30), True,
        "Как прошёл ужин? Запиши его 🍽", "🍽 Записать", "/nutrition?meal=dinner",
    ),
    # Текст собирается из данных дня, см. day_summary_text
    ReminderType(
        "summary", "🌙 Итог дня", time(21, 0), False,
        "Итог дня 🌙", "📈 Посмотреть прогресс", "/stats",
    ),
    # По воскресеньям. Текст — из данных недели, см. week_summary_text
    ReminderType(
        "week", "📅 Итог недели", time(19, 0), False,
        "Итоги недели 📅", "📈 Посмотреть прогресс", "/stats", weekday=6,
    ),
    # Без кнопки: перед сном приложение открывать незачем
    ReminderType(
        "bedtime", "🛌 Отбой", time(22, 30), False,
        "Пора готовиться ко сну 🛌\nОтложи телефон и приглуши свет — завтра скажешь себе спасибо.",
        "", "",
    ),
)  # fmt: skip
WEEKDAY_NAMES = ("пн", "вт", "ср", "чт", "пт", "сб", "вс")
REMINDERS_BY_KIND: dict[str, ReminderType] = {t.kind: t for t in REMINDER_TYPES}
MEAL_KINDS = frozenset({"breakfast", "lunch", "dinner"})

# Сдвиги времени кнопками в боте, минуты
SHIFT_STEPS = (-60, -15, 15, 60)
# Пропущенное (перезапуск, деплой) досылаем, если опоздали не больше чем на это время
LATE_WINDOW = timedelta(minutes=60)


@dataclass(frozen=True, slots=True)
class ReminderSetting:
    on: bool
    time: time


@dataclass(frozen=True, slots=True)
class Outgoing:
    """Напоминание к отправке."""

    user_id: int
    chat_id: int
    type: ReminderType
    # Дата в часовом поясе пользователя — на неё пишет быстрый чек-ин
    day: date
    # Текст и экран под данные пользователя. None — как в типе напоминания
    text: str | None = None
    path: str | None = None


@dataclass(frozen=True, slots=True)
class DayFacts:
    """Что записано за день — для вечернего итога."""

    kcal: float | None
    kcal_target: int | None
    water_ml: int
    water_target_ml: int
    workouts: int
    checkin: bool
    streak: int


def parse_settings(raw: Mapping[str, Any]) -> dict[str, ReminderSetting]:
    """Настройки из БД. Отсутствующие или битые значения — по умолчанию."""
    result: dict[str, ReminderSetting] = {}
    for t in REMINDER_TYPES:
        on, at = t.default_on, t.default_time
        item = raw.get(t.kind)
        if isinstance(item, dict):
            if isinstance(item.get("on"), bool):
                on = item["on"]
            if isinstance(item.get("time"), str):
                try:
                    at = time.fromisoformat(item["time"])
                except ValueError:
                    pass
        result[t.kind] = ReminderSetting(on=on, time=at.replace(second=0, microsecond=0))
    return result


def dump_settings(settings: Mapping[str, ReminderSetting]) -> dict[str, Any]:
    return {k: {"on": s.on, "time": s.time.strftime("%H:%M")} for k, s in settings.items()}


def shift_time(at: time, minutes: int) -> time:
    """Сдвигает время по кругу суток: 23:30 + 60 мин = 00:30."""
    total = (at.hour * 60 + at.minute + minutes) % (24 * 60)
    return time(total // 60, total % 60)


def due_kinds(settings: Mapping[str, ReminderSetting], local_now: datetime) -> Iterator[str]:
    """Включённые напоминания, время которых наступило не дольше LATE_WINDOW назад."""
    for kind, s in settings.items():
        if not s.on:
            continue
        weekday = REMINDERS_BY_KIND[kind].weekday
        if weekday is not None and local_now.weekday() != weekday:
            continue
        at = datetime.combine(local_now.date(), s.time, tzinfo=local_now.tzinfo)
        if at <= local_now < at + LATE_WINDOW:
            yield kind


def _liters(ml: int) -> str:
    return f"{ml / 1000:.1f}".replace(".", ",")


def day_summary_text(facts: DayFacts) -> str | None:
    """Вечерний итог. None — за день ничего нет и серии нет: писать незачем."""
    lines: list[str] = []
    if facts.kcal is not None:
        target = f" из {facts.kcal_target}" if facts.kcal_target else ""
        lines.append(f"🍽 {round(facts.kcal)}{target} ккал")
    if facts.water_ml > 0:
        lines.append(f"💧 {_liters(facts.water_ml)} из {_liters(facts.water_target_ml)} л")
    if facts.workouts:
        lines.append("🏋️ Тренировка выполнена")
    if facts.checkin:
        lines.append("😴 Чек-ин есть")

    if not lines:
        if facts.streak == 0:
            return None
        days = f"{facts.streak} {streaks.days_word(facts.streak)}"
        return (
            f"Сегодня ещё нет записей — серия {days} может прерваться 🔥\n"
            "Хватит одной записи до полуночи: еда, вода, вес или чек-ин."
        )

    text = "Итог дня 🌙\n" + "\n".join(lines)
    if facts.streak > 1:
        text += f"\n🔥 Серия: {facts.streak} {streaks.days_word(facts.streak)} подряд"
    return text


def _fmt_minutes(minutes: float) -> str:
    total = round(minutes)
    return f"{total // 60} ч {total % 60} мин" if total % 60 else f"{total // 60} ч"


def _has_data(d: DayStats) -> bool:
    scores = (d.sleep_minutes, d.sleep_quality, d.energy, d.mood, d.stress)
    return (
        d.kcal is not None
        or d.weight_kg is not None
        or d.workouts > 0
        or any(v is not None for v in scores)
    )


def week_summary_text(days: Sequence[DayStats], streak: int) -> str | None:
    """Итоги недели. None — за неделю ни одной записи: писать незачем."""
    active = sum(1 for d in days if _has_data(d))
    if active == 0 and streak == 0:
        return None

    lines = [f"📆 Дней с записями: {active} из {len(days)}"]
    kcal = [d.kcal for d in days if d.kcal is not None]
    if kcal:
        lines.append(f"🍽 В среднем {round(sum(kcal) / len(kcal))} ккал в день")
    sleep = [d.sleep_minutes for d in days if d.sleep_minutes is not None]
    if sleep:
        lines.append(f"😴 Сон в среднем {_fmt_minutes(sum(sleep) / len(sleep))}")
    workouts = sum(d.workouts for d in days)
    if workouts:
        lines.append(f"🏋️ Тренировок: {workouts}")
    weights = [d.weight_kg for d in days if d.weight_kg is not None]
    if len(weights) >= 2:
        delta = weights[-1] - weights[0]
        sign = "+" if delta > 0 else "−" if delta < 0 else "±"
        lines.append(f"⚖️ Вес: {sign}{abs(delta):.1f} кг".replace(".", ","))
    if streak > 1:
        lines.append(f"🔥 Серия: {streak} {streaks.days_word(streak)} подряд")
    return "Итоги недели 📅\n" + "\n".join(lines)


async def _planned_workout_id(session: AsyncSession, user: User, day: date) -> int | None:
    workouts = await WorkoutRepository(session).list_range(user.id, day, day)
    planned = [w for w in workouts if w.status == "planned"]
    # list_range отдаёт новые первыми — напоминаем о самой ранней из запланированных
    return planned[-1].id if planned else None


async def _day_facts(session: AsyncSession, user: User, day: date) -> DayFacts:
    stats = StatsRepository(session)
    kcal = (await stats.daily_kcal(user.id, day, day)).get(day)
    targets = await get_targets(session, user)
    water_day = await water.get_day(session, user, day)
    count, _ = (await stats.daily_workouts(user.id, day, day)).get(day, (0, 0.0))
    return DayFacts(
        kcal=kcal,
        kcal_target=targets.targets.kcal if targets else None,
        water_ml=water_day.ml,
        water_target_ml=water_day.target_ml,
        workouts=count,
        checkin=await CheckinRepository(session).exists(user.id, day),
        streak=(await streaks.get_streak(session, user)).current,
    )


async def _compose(
    session: AsyncSession, user: User, kind: str, day: date
) -> tuple[str | None, str | None] | None:
    """Текст и экран под данные пользователя. None — отправлять незачем."""
    if kind == "workout":
        workout_id = await _planned_workout_id(session, user, day)
        return None if workout_id is None else (None, f"/workouts/{workout_id}")
    if kind == "summary":
        text = day_summary_text(await _day_facts(session, user, day))
        return None if text is None else (text, None)
    if kind == "week":
        week = await get_summary(session, user, 7)
        streak = (await streaks.get_streak(session, user)).current
        text = week_summary_text(week, streak)
        return None if text is None else (text, None)
    return None, None


async def get_settings(session: AsyncSession, user: User) -> dict[str, ReminderSetting]:
    return parse_settings(await ReminderRepository(session).get_reminders(user.id))


async def _update(
    session: AsyncSession, user: User, kind: str, on: bool | None = None, minutes: int = 0
) -> dict[str, ReminderSetting]:
    settings = await get_settings(session, user)
    current = settings[kind]
    settings[kind] = ReminderSetting(
        on=current.on if on is None else on, time=shift_time(current.time, minutes)
    )
    await ReminderRepository(session).save_reminders(user.id, dump_settings(settings))
    await session.commit()
    return settings


async def toggle(session: AsyncSession, user: User, kind: str) -> dict[str, ReminderSetting]:
    """Включает или выключает напоминание."""
    current = (await get_settings(session, user))[kind]
    return await _update(session, user, kind, on=not current.on)


async def shift(
    session: AsyncSession, user: User, kind: str, minutes: int
) -> dict[str, ReminderSetting]:
    """Сдвигает время напоминания на minutes минут."""
    return await _update(session, user, kind, minutes=minutes)


async def disable_all(session: AsyncSession, user: User) -> None:
    """Выключает все напоминания — например, если пользователь заблокировал бота."""
    settings = await get_settings(session, user)
    off = {k: ReminderSetting(on=False, time=s.time) for k, s in settings.items()}
    await ReminderRepository(session).save_reminders(user.id, dump_settings(off))
    await session.commit()


async def _already_done(session: AsyncSession, user: User, kind: str, day: date) -> bool:
    """Данные уже внесены — напоминать незачем."""
    if kind in MEAL_KINDS:
        meals = await MealRepository(session).list_for_day(user.id, day)
        return any(m.meal_type == kind and m.items for m in meals)
    if kind == "water":
        water_day = await water.get_day(session, user, day)
        return water_day.ml >= water_day.target_ml
    return False


async def collect_due(session: AsyncSession, now: datetime) -> list[Outgoing]:
    """Напоминания, которые пора отправить. Отмечает их обработанными до отправки.

    Отметка до отправки защищает от дублей: если два процесса работают одновременно
    (например, во время деплоя), отметку получит только один.
    """
    repo = ReminderRepository(session)
    # Местная дата отличается от UTC максимум на сутки
    handled = await repo.handled_since(now.date() - timedelta(days=1))
    result: list[Outgoing] = []
    for user, raw in await repo.list_recipients():
        try:
            local_now = now.astimezone(ZoneInfo(user.timezone))
        except (ZoneInfoNotFoundError, ValueError):
            continue
        day = local_now.date()
        for kind in due_kinds(parse_settings(raw), local_now):
            if (user.id, kind, day) in handled:
                continue
            done = await _already_done(session, user, kind, day)
            if not await repo.mark_handled(user.id, kind, day) or done:
                continue
            composed = await _compose(session, user, kind, day)
            if composed is None:
                continue
            text, path = composed
            result.append(
                Outgoing(user.id, user.telegram_id, REMINDERS_BY_KIND[kind], day, text, path)
            )
    await session.commit()
    return result
