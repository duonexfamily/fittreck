"""quick meal items, food_favorites

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-04

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007"
down_revision: str | None = "0006"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Быстрая запись хранит только КБЖУ, граммовки у неё нет
    op.alter_column("meal_items", "grams", existing_type=sa.Numeric(6, 1), nullable=True)

    op.create_table(
        "food_favorites",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("food_id", sa.BigInteger(), nullable=False),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_food_favorites_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["food_id"],
            ["foods.id"],
            name=op.f("fk_food_favorites_food_id_foods"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_food_favorites")),
        sa.UniqueConstraint("user_id", "food_id", name=op.f("uq_food_favorites_user_id")),
    )
    op.create_index(op.f("ix_food_favorites_user_id"), "food_favorites", ["user_id"])
    op.create_index(op.f("ix_food_favorites_food_id"), "food_favorites", ["food_id"])
    op.execute("ALTER TABLE food_favorites ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_index(op.f("ix_food_favorites_food_id"), table_name="food_favorites")
    op.drop_index(op.f("ix_food_favorites_user_id"), table_name="food_favorites")
    op.drop_table("food_favorites")
    # Быстрые записи без граммовки в старой схеме не помещаются
    op.execute("DELETE FROM meal_items WHERE grams IS NULL")
    op.alter_column("meal_items", "grams", existing_type=sa.Numeric(6, 1), nullable=False)
