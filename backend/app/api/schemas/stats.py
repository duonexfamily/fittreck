from pydantic import BaseModel


class StreakOut(BaseModel):
    # Дней подряд с записями. Пока сегодня пусто, серия считается по вчера
    current: int
    best: int
    today_done: bool
    # Последние 7 дней, от старых к новым, последний — сегодня
    week: list[bool]
