import datetime as dt
from decimal import Decimal

from sqlalchemy import (
    BigInteger,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    SmallInteger,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base, TimestampMixin


class Exercise(TimestampMixin, Base):
    """Каталог упражнений. owner_id = None — системное упражнение."""

    __tablename__ = "exercises"
    __table_args__ = (
        # Поиск по подстроке (ILIKE) — триграммный индекс, как у продуктов
        Index(
            "ix_exercises_name_trgm",
            "name",
            postgresql_using="gin",
            postgresql_ops={"name": "gin_trgm_ops"},
        ),
    )

    name: Mapped[str] = mapped_column(String(128))
    muscle_group: Mapped[str] = mapped_column(String(16))
    # strength — повторения × вес, cardio — время и дистанция, stretch — на время
    kind: Mapped[str] = mapped_column(String(16))
    owner_id: Mapped[int | None] = mapped_column(
        BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True
    )


class Workout(TimestampMixin, Base):
    """Тренировка. planned — не завершена (идёт или запланирована), done — выполнена."""

    __tablename__ = "workouts"
    __table_args__ = (Index("ix_workouts_user_id_date", "user_id", "date"),)

    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"))
    # Дата в часовом поясе пользователя
    date: Mapped[dt.date] = mapped_column(Date)
    status: Mapped[str] = mapped_column(String(16))
    started_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    finished_at: Mapped[dt.datetime | None] = mapped_column(DateTime(timezone=True))
    # Субъективная нагрузка 1–10
    rpe: Mapped[int | None] = mapped_column(SmallInteger)
    note: Mapped[str | None] = mapped_column(String(1000))

    sets: Mapped[list["WorkoutSet"]] = relationship(
        back_populates="workout", order_by="WorkoutSet.id", cascade="all, delete-orphan"
    )


class WorkoutSet(TimestampMixin, Base):
    """Подход. Заполнены поля, подходящие виду упражнения."""

    __tablename__ = "workout_sets"

    workout_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("workouts.id", ondelete="CASCADE"), index=True
    )
    exercise_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("exercises.id", ondelete="CASCADE"), index=True
    )
    # Номер подхода внутри упражнения в этой тренировке, с 1
    set_no: Mapped[int] = mapped_column(SmallInteger)
    reps: Mapped[int | None] = mapped_column(Integer)
    weight_kg: Mapped[Decimal | None] = mapped_column(Numeric(5, 2))
    duration_s: Mapped[int | None] = mapped_column(Integer)
    distance_m: Mapped[int | None] = mapped_column(Integer)

    workout: Mapped[Workout] = relationship(back_populates="sets")
    exercise: Mapped[Exercise] = relationship()
