"""workout_sets.done, workout_templates, template_sets

Revision ID: 0010
Revises: 0009
Create Date: 2026-11-05

"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010"
down_revision: str | None = "0009"
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
    # Уже записанные подходы считаются выполненными
    op.add_column(
        "workout_sets",
        sa.Column("done", sa.Boolean(), server_default=sa.true(), nullable=False),
    )

    op.create_table(
        "workout_templates",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("name", sa.String(length=64), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["user_id"],
            ["users.id"],
            name=op.f("fk_workout_templates_user_id_users"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_workout_templates")),
    )
    op.create_index(op.f("ix_workout_templates_user_id"), "workout_templates", ["user_id"])

    op.create_table(
        "template_sets",
        sa.Column("id", sa.BigInteger(), sa.Identity(), nullable=False),
        sa.Column("template_id", sa.BigInteger(), nullable=False),
        sa.Column("exercise_id", sa.BigInteger(), nullable=False),
        sa.Column("position", sa.SmallInteger(), nullable=False),
        sa.Column("reps", sa.Integer(), nullable=True),
        sa.Column("weight_kg", sa.Numeric(precision=5, scale=2), nullable=True),
        sa.Column("duration_s", sa.Integer(), nullable=True),
        sa.Column("distance_m", sa.Integer(), nullable=True),
        *_timestamps(),
        sa.ForeignKeyConstraint(
            ["template_id"],
            ["workout_templates.id"],
            name=op.f("fk_template_sets_template_id_workout_templates"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["exercise_id"],
            ["exercises.id"],
            name=op.f("fk_template_sets_exercise_id_exercises"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_template_sets")),
    )
    op.create_index(op.f("ix_template_sets_template_id"), "template_sets", ["template_id"])
    op.create_index(op.f("ix_template_sets_exercise_id"), "template_sets", ["exercise_id"])

    for table in ("workout_templates", "template_sets"):
        op.execute(f"ALTER TABLE {table} ENABLE ROW LEVEL SECURITY")


def downgrade() -> None:
    op.drop_table("template_sets")
    op.drop_table("workout_templates")
    op.drop_column("workout_sets", "done")
