import datetime as dt

from pydantic import BaseModel


class StreakOut(BaseModel):
    # Дней подряд с записями. Пока сегодня пусто, серия считается по вчера
    current: int
    best: int
    today_done: bool
    # Последние 7 дней, от старых к новым, последний — сегодня
    week: list[bool]


class DayStatsOut(BaseModel):
    # null — за день нет данных
    date: dt.date
    weight_kg: float | None
    kcal: float | None
    sleep_minutes: int | None
    sleep_quality: int | None
    energy: int | None
    stress: int | None
    mood: int | None
    workouts: int
    # Повторы × вес по выполненным подходам
    volume_kg: float
