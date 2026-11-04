"""Наблюдения по данным пользователя: как сон, тренировки и питание связаны с самочувствием и весом.

Это сравнение средних по его же дням, а не медицинский вывод. Показываем только заметную
разницу и только когда в каждой группе хватает дней.
"""

from collections.abc import Callable, Sequence

from app.services.stats import DayStats

# Сон от 7 часов считаем достаточным
GOOD_SLEEP_MINUTES = 7 * 60
# Меньше дней в группе — сравнение случайно
MIN_DAYS = 3
# Разница оценок 1–5, которую стоит показать
MIN_SCORE_DIFF = 0.3
# Для вывода о калориях и весе
MIN_KCAL_DAYS = 5
MIN_WEIGHT_SPAN_DAYS = 7


def _fmt(v: float) -> str:
    return f"{v:.1f}".replace(".", ",")


def _mean(values: Sequence[float]) -> float:
    return sum(values) / len(values)


def _compare(
    days: Sequence[DayStats],
    group: Callable[[DayStats], bool | None],
    score: Callable[[DayStats], int | None],
) -> tuple[float, float] | None:
    """Средняя оценка в днях группы и вне её. None — мало данных или разница незаметна."""
    yes: list[float] = []
    no: list[float] = []
    for d in days:
        value, in_group = score(d), group(d)
        if value is None or in_group is None:
            continue
        (yes if in_group else no).append(value)
    if len(yes) < MIN_DAYS or len(no) < MIN_DAYS:
        return None
    a, b = _mean(yes), _mean(no)
    return (a, b) if abs(a - b) >= MIN_SCORE_DIFF else None


def _good_sleep(d: DayStats) -> bool | None:
    return None if d.sleep_minutes is None else d.sleep_minutes >= GOOD_SLEEP_MINUTES


def compute_insights(days: Sequence[DayStats], kcal_target: int | None) -> list[str]:
    """Короткие наблюдения простыми словами. Пустой список — данных пока мало."""
    result: list[str] = []

    for label, score in (
        ("энергия", lambda d: d.energy),
        ("настроение", lambda d: d.mood),
    ):
        pair = _compare(days, _good_sleep, score)
        if pair:
            result.append(
                f"😴 После 7+ часов сна {label} в среднем {_fmt(pair[0])} из 5, "
                f"после короткого сна — {_fmt(pair[1])}."
            )

    pair = _compare(days, lambda d: d.workouts > 0, lambda d: d.mood)
    if pair:
        result.append(
            f"🏋️ В дни с тренировкой настроение {_fmt(pair[0])} из 5, без неё — {_fmt(pair[1])}."
        )

    kcal = [d.kcal for d in days if d.kcal is not None]
    weights = [(d.date, d.weight_kg) for d in days if d.weight_kg is not None]
    if len(kcal) >= MIN_KCAL_DAYS and len(weights) >= 2:
        (first_day, first), (last_day, last) = weights[0], weights[-1]
        if (last_day - first_day).days >= MIN_WEIGHT_SPAN_DAYS:
            delta = last - first
            sign = "+" if delta > 0 else "−" if delta < 0 else "±"
            norm = f" при норме {kcal_target}" if kcal_target else ""
            result.append(
                f"⚖️ В среднем {round(_mean(kcal))} ккал в день{norm} — "
                f"вес за это время {sign}{_fmt(abs(delta))} кг."
            )
    return result
