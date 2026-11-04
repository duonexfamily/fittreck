import datetime as dt

from sqlalchemy import BigInteger, Date, ForeignKey, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class WaterLog(TimestampMixin, Base):
    """Выпитая вода. Одна запись на пользователя в день, хранится сумма за день."""

    __tablename__ = "water_logs"
    __table_args__ = (UniqueConstraint("user_id", "date"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Дата в часовом поясе пользователя
    date: Mapped[dt.date] = mapped_column(Date)
    ml: Mapped[int] = mapped_column(Integer, default=0)
