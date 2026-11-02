from datetime import date, datetime

from sqlalchemy import BigInteger, Date, DateTime, SmallInteger, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class User(TimestampMixin, Base):
    __tablename__ = "users"

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    first_name: Mapped[str] = mapped_column(String(128))
    username: Mapped[str | None] = mapped_column(String(64))
    language_code: Mapped[str | None] = mapped_column(String(16))

    # Анкета — заполняется в Mini App при первом входе
    sex: Mapped[str | None] = mapped_column(String(8))
    birth_date: Mapped[date | None] = mapped_column(Date)
    height_cm: Mapped[int | None] = mapped_column(SmallInteger)
    goal: Mapped[str | None] = mapped_column(String(16))
    activity_level: Mapped[str | None] = mapped_column(String(16))
    timezone: Mapped[str] = mapped_column(String(64), server_default="Europe/Moscow")
    onboarded_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
