import datetime as dt

from sqlalchemy import BigInteger, Date, ForeignKey, SmallInteger, String, Time, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Checkin(TimestampMixin, Base):
    """Ежедневный чек-ин: сон за прошлую ночь и самочувствие. Одна запись на пользователя в день."""

    __tablename__ = "checkins"
    __table_args__ = (UniqueConstraint("user_id", "date"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Дата пробуждения в часовом поясе пользователя
    date: Mapped[dt.date] = mapped_column(Date)
    # Время на часах пользователя, а не момент: отход ко сну обычно накануне вечером
    bed_time: Mapped[dt.time | None] = mapped_column(Time)
    wake_time: Mapped[dt.time | None] = mapped_column(Time)
    # Оценки 1–5
    sleep_quality: Mapped[int | None] = mapped_column(SmallInteger)
    energy: Mapped[int | None] = mapped_column(SmallInteger)
    stress: Mapped[int | None] = mapped_column(SmallInteger)
    mood: Mapped[int | None] = mapped_column(SmallInteger)
    note: Mapped[str | None] = mapped_column(String(1000))
