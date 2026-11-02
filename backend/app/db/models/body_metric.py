import datetime as dt
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class BodyMetric(TimestampMixin, Base):
    """Замеры тела. Одна запись на пользователя в день."""

    __tablename__ = "body_metrics"
    __table_args__ = (UniqueConstraint("user_id", "date"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Дата в часовом поясе пользователя
    date: Mapped[dt.date] = mapped_column(Date)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
