import datetime as dt
from typing import Any

from sqlalchemy import BigInteger, Date, ForeignKey, String, UniqueConstraint, text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class UserSettings(TimestampMixin, Base):
    """Настройки пользователя.

    Строка создаётся при первом изменении, до этого действуют значения по умолчанию.
    """

    __tablename__ = "user_settings"

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), unique=True
    )
    # Напоминания: {"lunch": {"on": true, "time": "13:30"}, ...}. Нет ключа — значение по умолчанию
    reminders: Mapped[dict[str, Any]] = mapped_column(
        JSONB, default=dict, server_default=text("'{}'::jsonb")
    )


class ReminderLog(TimestampMixin, Base):
    """Напоминание за день уже обработано: отправлено или не нужно (данные внесены)."""

    __tablename__ = "reminder_log"
    __table_args__ = (UniqueConstraint("user_id", "type", "sent_on"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    type: Mapped[str] = mapped_column(String(16))
    # Дата в часовом поясе пользователя
    sent_on: Mapped[dt.date] = mapped_column(Date, index=True)
