from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base, TimestampMixin


class Food(TimestampMixin, Base):
    """Справочник продуктов. КБЖУ на 100 г. owner_id = None — системный продукт."""

    __tablename__ = "foods"
    __table_args__ = (
        # Поиск по подстроке (ILIKE) — триграммный индекс, расширение pg_trgm
        Index(
            "ix_foods_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    name: Mapped[str] = mapped_column(String(128))
    kcal: Mapped[Decimal] = mapped_column(Numeric(6, 1))
    protein: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    fat: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    carbs: Mapped[Decimal] = mapped_column(Numeric(5, 1))
    owner_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


class FoodFavorite(TimestampMixin, Base):
    """Избранный продукт пользователя. Один продукт — одна отметка."""

    __tablename__ = "food_favorites"
    __table_args__ = (UniqueConstraint("user_id", "food_id"),)

    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    food_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("foods.id", ondelete="CASCADE"), index=True
    )
