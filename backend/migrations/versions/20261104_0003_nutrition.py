"""foods, meals, meal_items

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _timestamps() -> list[sa.Column[sa.DateTime]]:
    return [
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    ]


def upgrade() -> None:
    # Триграммный поиск по названию продукта. Расширение не удаляем при откате: оно общее для БД
    op.execute("CREATE EXTENSION IF NOT EXISTS pg_trgm")

    op.create_table(
        "foods",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("kcal", sa.Numeric(precision=6, scale=1), nullable=False),
        sa.Column("protein", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("fat", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("carbs", sa.Numeric(precision=5, scale=1), nullable=False),
        sa.Column("owner_id", sa.BigInteger(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["owner_id"], ["users.id"], name=op.f("fk_foods_owner_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_foods")),
    )
    op.create_index(op.f("ix_foods_owner_id"), "foods", ["owner_id"])
    op.create_index(
        "ix_foods_name_trgm",
        "foods",
        ["name"],
        postgresql_using="gin",
        postgresql_ops={"name": "gin_trgm_ops"},
    )

    op.create_table(
        "meals",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("meal_type", sa.String(length=16), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"], name=op.f("fk_meals_user_id_users"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meals")),
        sa.UniqueConstraint("user_id", "date", "meal_type", name=op.f("uq_meals_user_id")),
    )
    op.create_index(op.f("ix_meals_user_id"), "meals", ["user_id"])

    op.create_table(
        "meal_items",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("meal_id", sa.BigInteger(), nullable=False),
        sa.Column("food_id", sa.BigInteger(), nullable=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("grams", sa.Numeric(precision=6, scale=1), nullable=False),
        sa.Column("kcal", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("protein", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("fat", sa.Numeric(precision=7, scale=2), nullable=False),
        sa.Column("carbs", sa.Numeric(precision=7, scale=2), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["meal_id"], ["meals.id"], name=op.f("fk_meal_items_meal_id_meals"), ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["food_id"], ["foods.id"], name=op.f("fk_meal_items_food_id_foods"), ondelete="SET NULL"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_meal_items")),
    )
    op.create_index(op.f("ix_meal_items_meal_id"), "meal_items", ["meal_id"])
    op.create_index(op.f("ix_meal_items_food_id"), "meal_items", ["food_id"])

    for table in ("foods", "meals", "meal_items"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("meal_items")
    op.drop_table("meals")
    op.drop_table("foods")
