import datetime as dt
from decimal import Decimal

from sqlalchemy import BigInteger, Date, ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Meal(TimestampMixin, Base):
    """Приём пищи. Один приём каждого типа на пользователя в день."""

    __tablename__ = "meals"
    __table_args__ = (UniqueConstraint("user_id", "date", "meal_type"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    # Дата в часовом поясе пользователя
    date: Mapped[dt.date] = mapped_column(Date)
    meal_type: Mapped[str] = mapped_column(String(16))

    items: Mapped[list["MealItem"]] = relationship(
        back_populates="meal", order_by="MealItem.id", cascade="all, delete-orphan"
    )


class MealItem(TimestampMixin, Base):
    """Продукт в приёме пищи. КБЖУ — снимок на указанную граммовку."""

    __tablename__ = "meal_items"

    meal_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("meals.id", ondelete="CASCADE"), index=True
    )
    # Удаление продукта из справочника не трогает историю
    food_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("foods.id", ondelete="SET NULL"), index=True
    )
    name: Mapped[str] = mapped_column(String(128))
    # None — быстрая запись: КБЖУ введены вручную, без продукта и граммовки
    grams: Mapped[Decimal | None] = mapped_column(Numeric(6, 1))
    kcal: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    protein: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    fat: Mapped[Decimal] = mapped_column(Numeric(7, 2))
    carbs: Mapped[Decimal] = mapped_column(Numeric(7, 2))

    meal: Mapped[Meal] = relationship(back_populates="items")
